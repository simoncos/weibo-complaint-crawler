"""Build separated model-input and sealed-gold benchmark files.

The model-facing file omits platform URLs, profile attributes, exact times and
official adjudication text. Free-text redaction is conservative and still
requires human privacy review before any third-party API run.
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path

from analysis.load import iter_complaints
from analysis.official_parser import parse_official
from analysis.reporter_features import extract_report_features


_RE_URL = re.compile(r'https?://\S+', re.I)
_RE_HANDLE = re.compile(r'@[\w\-\u3400-\u9fff]{2,}')
_RE_CONTACT = re.compile(
    r'(?i)(?:qq|微信|电话|手机)[\s:：号]*[\w\-]{5,}|(?<!\d)1[3-9]\d{9}(?!\d)')


def era_from_time(value):
    value = (value or '').strip()
    if len(value) < 4 or not value[:4].isdigit():
        return 'unknown'
    year = int(value[:4])
    if 2012 <= year <= 2013:
        return 'era_2012_2013'
    if 2014 <= year <= 2016:
        return 'era_2014_2016'
    if 2017 <= year <= 2018:
        return 'era_2017_2018'
    return 'outside_study_window'


def redact_text(text):
    text = _RE_URL.sub('[URL]', text or '')
    text = _RE_HANDLE.sub('[HANDLE]', text)
    text = _RE_CONTACT.sub('[CONTACT]', text)
    return text.strip()


def policy_date_from_time(value):
    match = re.match(r'^(\d{4}-\d{2}-\d{2})', (value or '').strip())
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1)).isoformat()
    except ValueError:
        return None


def build_case(complaint, case_id):
    official_text = (complaint.get('official') or {}).get('official_text')
    gold = parse_official(official_text)
    rumor = complaint.get('rumor') or {}
    rumor_text = rumor.get('rumor_text')
    if not rumor_text or gold['verdict'] is None:
        return None
    verdict = {'upheld_informal': 'upheld'}.get(gold['verdict'], gold['verdict'])
    if verdict not in ('upheld', 'rejected', 'undetermined'):
        return None

    post_time = rumor.get('rumor_time')
    policy_date = policy_date_from_time(post_time)
    if not policy_date:
        return None
    era = era_from_time(post_time)
    reported_post = rumor_text
    rumorer_name = rumor.get('rumorer_name')
    if rumorer_name and reported_post.startswith(rumorer_name):
        reported_post = reported_post[len(rumorer_name):].lstrip('：: ')

    reports = []
    for index, raw_reporter in enumerate(complaint.get('reports') or [], 1):
        features = extract_report_features(raw_reporter)
        if not features['has_statement']:
            continue
        reports.append({
            'reporter_alias': f'reporter_{index:02d}',
            'reporter_type': features['reporter_type'],
            'report_year': (features['report_time'] or '')[:4] or None,
            'statement': redact_text(features['statement']),
        })

    input_record = {
        'case_id': case_id,
        'era': era,
        'policy_date': policy_date,
        'input': {
            'reported_post': redact_text(reported_post),
            'reported_user': {'alias': 'reported_user'},
            'post_year': policy_date[:4],
            'reports': reports,
            'visible_reporter_count': len(complaint.get('reports') or []),
            'actual_reporter_count': complaint.get('actual_reporter_count'),
        },
    }
    gold_record = {
        'case_id': case_id,
        'era': era,
        'gold': {
            'verdict': verdict,
            'cited_articles': gold['cited_articles'],
            'penalties': gold['penalties'],
        },
    }
    linkage_record = {
        'case_id': case_id,
        'source_url': complaint.get('url'),
        'official_text': official_text,
    }
    return input_record, gold_record, linkage_record


def build_instance(complaint, case_id='synthetic-case'):
    """Compatibility helper for unit tests; returns input plus sealed gold."""
    built = build_case(complaint, case_id)
    if not built:
        return None
    input_record, gold_record, _ = built
    return {**input_record, 'gold': gold_record['gold']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', help='restricted source dump')
    parser.add_argument('inputs_out', help='model-facing input JSONL')
    parser.add_argument('--gold-out', required=True, help='sealed gold JSONL')
    parser.add_argument('--linkage-out', help='optional restricted source linkage JSONL')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        parser.error('--limit must be positive')

    source = Path(args.dump).resolve()
    outputs = [Path(args.inputs_out).resolve(), Path(args.gold_out).resolve()]
    if args.linkage_out:
        outputs.append(Path(args.linkage_out).resolve())
    if len(outputs) != len(set(outputs)):
        parser.error('inputs, gold and linkage outputs must be different files')
    if source in outputs:
        parser.error('an output path must not overwrite the source dump')
    existing = [path for path in outputs if path.exists()]
    if existing and not args.overwrite:
        parser.error(
            f'output already exists (use --overwrite intentionally): {existing[0]}')

    n_in = n_out = 0
    linkage_file = (
        open(args.linkage_out, 'w', encoding='utf-8') if args.linkage_out else None)
    try:
        with open(args.inputs_out, 'w', encoding='utf-8') as inputs_file, \
             open(args.gold_out, 'w', encoding='utf-8') as gold_file:
            for complaint in iter_complaints(args.dump):
                n_in += 1
                case_id = f'case-{n_in:06d}'
                built = build_case(complaint, case_id)
                if not built:
                    continue
                input_record, gold_record, linkage_record = built
                inputs_file.write(json.dumps(input_record, ensure_ascii=False) + '\n')
                gold_file.write(json.dumps(gold_record, ensure_ascii=False) + '\n')
                if linkage_file:
                    linkage_file.write(json.dumps(linkage_record, ensure_ascii=False) + '\n')
                n_out += 1
                if args.limit and n_out >= args.limit:
                    break
    finally:
        if linkage_file:
            linkage_file.close()
    print(f'{n_out}/{n_in} cases -> {args.inputs_out}; sealed gold -> {args.gold_out}')


if __name__ == '__main__':
    main()
