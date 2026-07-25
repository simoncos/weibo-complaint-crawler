"""Run one frozen benchmark condition against model-facing inputs only.

No gold labels are loaded. A data-processing approval flag is required before
any third-party API call. Every case produces one success/refusal/error record
with prompt and runtime metadata so failures remain in the denominator.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

from benchmark.score import normalize_prediction_record


BASE_SYSTEM_PROMPT = """\
You are evaluating historical platform adjudication cases. Use only the case
materials supplied in the user message. Return one JSON object with:
- verdict: upheld, rejected, or undetermined
- cited_articles: a list of integer article numbers
- penalties: a list of {type, magnitude}; allowed types are credit_deduction,
  mute, follow_ban, delete_post, and account_closure
- reasoning_summary: a short explanation

Do not assume policy or distributional information that is not supplied by the
selected experimental condition.
"""

ERA_DESCRIPTIONS = {
    'era_2012_2013': '2012-2013 study period',
    'era_2014_2016': '2014-2016 study period',
    'era_2017_2018': '2017-2018 study period',
    'unknown': 'unknown period',
    'outside_study_window': 'outside the preregistered study window',
}

FORBIDDEN_MODEL_KEYS = {
    'gold', 'official', 'official_text', 'source_url', 'linkage',
    'rumorer_name', 'rumorer_url', 'reporter_name', 'reporter_url',
    'reporter_description', 'reporter_location', 'reporter_gender',
}


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_data_processing_approval(path, model, input_sha256):
    approval = json.loads(Path(path).read_text(encoding='utf-8'))
    if approval.get('approved') is not True:
        raise ValueError('data-processing record is not approved')
    approval_id = approval.get('approval_id')
    if not approval_id or str(approval_id).startswith('PENDING'):
        raise ValueError('data-processing record has no approval_id')
    if approval.get('provider') != 'anthropic':
        raise ValueError('data-processing approval is not for provider anthropic')
    if approval.get('purpose') != 'historical-adjudication-benchmark':
        raise ValueError('data-processing approval has the wrong purpose')
    if approval.get('approved_input_sha256') != input_sha256:
        raise ValueError('model-input SHA-256 does not match data-processing approval')
    allowed_models = approval.get('allowed_models')
    if not isinstance(allowed_models, list) or model not in allowed_models:
        raise ValueError(f'model {model!r} is not covered by data-processing approval')
    expires_on = approval.get('expires_on')
    if not expires_on or date.fromisoformat(expires_on) < date.today():
        raise ValueError('data-processing approval is missing or expired')
    return approval


def assert_model_facing_record(record):
    def walk(value, path):
        if isinstance(value, dict):
            forbidden = FORBIDDEN_MODEL_KEYS & set(value)
            if forbidden:
                raise ValueError(
                    f"{record.get('case_id')}: forbidden model-input key(s) "
                    f"at {path}: {sorted(forbidden)}")
            for key, child in value.items():
                walk(child, f'{path}.{key}')
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f'{path}[{index}]')
    walk(record, '$')


def load_rules_manifest(path):
    manifest_path = Path(path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('human_version_verified') is not True:
        raise ValueError('rules manifest is not human-version-verified')
    result = []
    for entry in manifest.get('periods', []):
        period_id = entry.get('id')
        effective_from = entry.get('effective_from')
        effective_to = entry.get('effective_to')
        if (not period_id or not effective_from or not effective_to
                or str(effective_from).startswith('PENDING')
                or str(effective_to).startswith('PENDING')):
            raise ValueError('rules manifest contains an unverified policy period')
        rule_path = (manifest_path.parent / entry['file']).resolve()
        text = rule_path.read_text(encoding='utf-8')
        if len(text.strip()) < 500:
            raise ValueError(f'{period_id}: verified rule text is unexpectedly short')
        actual_hash = sha256_text(text)
        expected_hash = entry.get('sha256')
        if not expected_hash or expected_hash.startswith('PENDING'):
            raise ValueError(f'{period_id}: rules manifest has no verified SHA-256')
        if actual_hash != expected_hash:
            raise ValueError(f'{period_id}: rule text SHA-256 mismatch')
        source = entry.get('source')
        if not source or str(source).startswith('PENDING'):
            raise ValueError(f'{period_id}: rules manifest has no verified source')
        parsed_from = date.fromisoformat(effective_from)
        parsed_to = date.fromisoformat(effective_to)
        if parsed_from > parsed_to:
            raise ValueError(f'{period_id}: policy period starts after it ends')
        result.append({
            'id': period_id,
            'effective_from': parsed_from,
            'effective_to': parsed_to,
            'text': text,
            'sha256': actual_hash,
            'source': source,
        })
    if not result:
        raise ValueError('rules manifest contains no verified policy periods')
    result.sort(key=lambda entry: entry['effective_from'])
    for previous, current in zip(result, result[1:]):
        if current['effective_from'] <= previous['effective_to']:
            raise ValueError(
                f"overlapping policy periods: {previous['id']} and "
                f"{current['id']}")
    return result


def rule_for_record(record, rules):
    raw_date = record.get('policy_date')
    if not raw_date:
        raise ValueError(f"{record.get('case_id')}: missing policy_date")
    policy_date = date.fromisoformat(raw_date)
    matches = [rule for rule in rules
               if rule['effective_from'] <= policy_date <= rule['effective_to']]
    if len(matches) != 1:
        raise ValueError(
            f"{record.get('case_id')}: expected one policy period for "
            f'{policy_date}, found {len(matches)}')
    return matches[0]


def system_prompt_for(record, condition, rules_by_era=None):
    era = record.get('era', 'unknown')
    prompt = BASE_SYSTEM_PROMPT
    metadata = {'condition': condition, 'era': era, 'rules_sha256': None}
    if condition not in {'zero_shot', 'era_hint', 'policy_prompt'}:
        raise ValueError(f'unknown experimental condition: {condition}')
    if condition == 'era_hint':
        prompt += ('\nCondition information: this case belongs to the '
                   f'{ERA_DESCRIPTIONS.get(era, era)}. Apply only '
                   'contemporaneous practice you can justify.\n')
    elif condition == 'policy_prompt':
        if not rules_by_era:
            raise ValueError('no verified policy periods configured')
        rule = rule_for_record(record, rules_by_era)
        prompt += ('\nCondition information: apply the following verified '
                   f'policy text for {ERA_DESCRIPTIONS.get(era, era)}.\n\n'
                   + rule['text'] + '\n')
        metadata['rules_sha256'] = rule['sha256']
        metadata['policy_period_id'] = rule['id']
    return prompt, metadata


def render_case(record):
    inp = record['input']
    lines = [
        '## Reported post', inp['reported_post'], '',
        f"Post year: {inp.get('post_year') or 'unknown'}", '',
        '## Reporter statements',
    ]
    for index, report in enumerate(inp.get('reports', []), 1):
        lines.append(
            f"{index}. [{report['reporter_alias']}; heuristic account type: "
            f"{report['reporter_type']}; report year: "
            f"{report.get('report_year') or 'unknown'}] {report['statement']}")
    if not inp.get('reports'):
        lines.append('(No reporter statement text is available.)')
    lines.append(
        f"Visible/actual reporter count: {inp.get('visible_reporter_count')} / "
        f"{inp.get('actual_reporter_count')}")
    return '\n'.join(lines)


def parse_model_json(text, case_id):
    stripped = text.strip()
    if stripped.startswith('```'):
        stripped = stripped.split('\n', 1)[1]
        stripped = stripped.rsplit('```', 1)[0]
    start, end = stripped.find('{'), stripped.rfind('}')
    if start < 0 or end < start:
        raise ValueError('model response does not contain a JSON object')
    parsed = json.loads(stripped[start:end + 1])
    _, normalized = normalize_prediction_record({'case_id': case_id, 'pred': parsed})
    normalized['reasoning_summary'] = parsed.get('reasoning_summary', '')
    return normalized


def response_text(response):
    return '\n'.join(
        block.text for block in response.content
        if getattr(block, 'type', None) == 'text' and getattr(block, 'text', None))


def run_case(client, record, model, system, max_tokens, max_attempts):
    user_prompt = render_case(record)
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0,
                system=system,
                messages=[{'role': 'user', 'content': user_prompt}],
            )
            if getattr(response, 'stop_reason', None) == 'refusal':
                return 'refusal', None, attempt, None
            prediction = parse_model_json(response_text(response), record['case_id'])
            return 'success', prediction, attempt, None
        except Exception as error:  # persisted; SDK/network errors vary by version
            last_error = f'{type(error).__name__}: {error}'
            if attempt < max_attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
    return 'error', None, max_attempts, last_error


def _load_existing_case_ids(path, expected_run):
    if not path.exists():
        return set()
    seen = set()
    with path.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                case_id = record.get('case_id')
                if not case_id:
                    raise ValueError('existing result record has no case_id')
                if case_id in seen:
                    raise ValueError(f'duplicate case_id in existing results: {case_id}')
                run = record.get('run') or {}
                for key, expected in expected_run.items():
                    if run.get(key) != expected:
                        raise ValueError(
                            f'resume configuration mismatch for {case_id}: '
                            f'{key}={run.get(key)!r}, expected {expected!r}')
                seen.add(case_id)
    return seen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', help='sampled model-facing inputs JSONL')
    parser.add_argument('--out', required=True)
    parser.add_argument('--condition', required=True,
                        choices=('zero_shot', 'era_hint', 'policy_prompt'))
    parser.add_argument('--model', default=os.environ.get('ANTHROPIC_MODEL'))
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--rules-manifest')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--max-tokens', type=int, default=2048)
    parser.add_argument('--max-attempts', type=int, default=3)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--data-processing-approval',
                        help='JSON approval record required for API calls')
    args = parser.parse_args(argv)
    if not args.model:
        parser.error('--model or ANTHROPIC_MODEL is required')
    if args.condition == 'policy_prompt' and not args.rules_manifest:
        parser.error('--rules-manifest is required for policy_prompt')
    if args.condition != 'policy_prompt' and args.rules_manifest:
        parser.error('--rules-manifest is only valid for policy_prompt')
    if not args.dry_run and not args.data_processing_approval:
        parser.error('--data-processing-approval is required for API calls')
    if args.limit is not None and args.limit <= 0:
        parser.error('--limit must be positive')
    if args.max_tokens <= 0 or args.max_attempts <= 0:
        parser.error('--max-tokens and --max-attempts must be positive')

    input_sha256 = sha256_file(args.inputs)
    approval = (
        load_data_processing_approval(
            args.data_processing_approval, args.model, input_sha256)
        if args.data_processing_approval else None)
    rules = load_rules_manifest(args.rules_manifest) if args.rules_manifest else None
    out_path = Path(args.out)
    if out_path.exists() and not args.resume:
        raise FileExistsError(f'refusing to overwrite existing output: {out_path}')
    completed = _load_existing_case_ids(out_path, {
        'run_id': args.run_id,
        'condition': args.condition,
        'model': args.model,
        'max_tokens': args.max_tokens,
        'model_input_sha256': input_sha256,
        'data_processing_approval_id': (
            approval.get('approval_id') if approval else None),
    }) if args.resume else set()

    anthropic_module = client = None
    sdk_version = None
    if not args.dry_run:
        import anthropic as anthropic_module
        sdk_version = importlib.metadata.version('anthropic')
        client = anthropic_module.Anthropic()

    planned = 0
    input_case_ids = set()
    mode = 'a' if args.resume else 'w'
    with open(args.inputs, encoding='utf-8') as inputs_file, \
         out_path.open(mode, encoding='utf-8') as output_file:
        for line in inputs_file:
            if not line.strip():
                continue
            record = json.loads(line)
            case_id = record['case_id']
            if case_id in input_case_ids:
                raise ValueError(f'duplicate case_id in model inputs: {case_id}')
            input_case_ids.add(case_id)
            assert_model_facing_record(record)
            if case_id in completed:
                continue
            if args.limit is not None and planned >= args.limit:
                break
            planned += 1
            system, condition_metadata = system_prompt_for(
                record, args.condition, rules)
            user_prompt = render_case(record)
            prompt_hash = sha256_text(system + '\n---USER---\n' + user_prompt)
            if args.dry_run:
                status, prediction, attempts, error = 'dry_run', None, 0, None
            else:
                status, prediction, attempts, error = run_case(
                    client, record, args.model, system,
                    args.max_tokens, args.max_attempts)
            result = {
                'case_id': case_id,
                'status': status,
                'pred': prediction,
                'error': error,
                'run': {
                    'run_id': args.run_id,
                    'condition': args.condition,
                    'model': args.model,
                    'anthropic_sdk': sdk_version,
                    'temperature': 0,
                    'max_tokens': args.max_tokens,
                    'attempts': attempts,
                    'prompt_sha256': prompt_hash,
                    'model_input_sha256': input_sha256,
                    'data_processing_approval_id': (
                        approval.get('approval_id') if approval else None),
                    'rules_sha256': condition_metadata['rules_sha256'],
                    'policy_period_id': condition_metadata.get('policy_period_id'),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                },
            }
            output_file.write(json.dumps(result, ensure_ascii=False) + '\n')
            output_file.flush()
            print(f'[{planned}] {case_id}: {status}')


if __name__ == '__main__':
    main()
