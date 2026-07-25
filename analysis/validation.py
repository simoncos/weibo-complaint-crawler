"""Create and score restricted human-validation sets for heuristic labels.

The generated JSONL contains real text when run on the full dump and must stay
inside the restricted data boundary. Two independent annotations plus an
adjudicated label are required for publication-grade validation.
"""

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict

from analysis.load import iter_complaints
from analysis.official_parser import parse_official
from analysis.reporter_features import extract_report_features


def _task_id(prefix, value):
    digest = hashlib.sha256((prefix + ':' + str(value)).encode('utf-8')).hexdigest()
    return f'{prefix}-{digest[:16]}'


def _pick_stratified(pools, per_stratum, seed):
    rng = random.Random(seed)
    picked = []
    for stratum in sorted(pools):
        pool = pools[stratum]
        picked.extend(pool if len(pool) <= per_stratum
                      else rng.sample(pool, per_stratum))
    rng.shuffle(picked)
    return picked


def build_validation_records(complaints, per_stratum=25, seed=42):
    official_pools = defaultdict(list)
    reporter_pools = defaultdict(list)
    for index, complaint in enumerate(complaints):
        official_text = (complaint.get('official') or {}).get('official_text')
        machine_official = parse_official(official_text)
        if official_text:
            stratum = machine_official['verdict'] or 'unparsed'
            official_pools[stratum].append({
                'task_id': _task_id('official', complaint.get('url') or index),
                'task': 'official_parser',
                'stratum': stratum,
                'restricted_text': official_text,
                'machine_label': machine_official,
                'annotator_a': None,
                'annotator_b': None,
                'adjudicated_label': None,
                'notes': '',
            })
        for report_index, raw_reporter in enumerate(complaint.get('reports') or []):
            features = extract_report_features(raw_reporter)
            reporter_type = features['reporter_type']
            reporter_pools[reporter_type].append({
                'task_id': _task_id(
                    'reporter', f'{complaint.get("url") or index}:{report_index}'),
                'task': 'reporter_type',
                'stratum': reporter_type,
                'restricted_text': raw_reporter.get('reporter_description') or '',
                'machine_label': reporter_type,
                'annotator_a': None,
                'annotator_b': None,
                'adjudicated_label': None,
                'notes': '',
            })
    return (
        _pick_stratified(official_pools, per_stratum, seed)
        + _pick_stratified(reporter_pools, per_stratum, seed + 1)
    )


def resolved_human_label(record):
    if record.get('adjudicated_label') is not None:
        return record['adjudicated_label'], 'adjudicated'
    a, b = record.get('annotator_a'), record.get('annotator_b')
    if a is not None and a == b:
        return a, 'agreement'
    return None, 'unresolved'


def _set_equal(left, right):
    return set(left or []) == set(right or [])


def _annotation_category(record, label):
    if record['task'] == 'reporter_type':
        return ('reporter_type', label)
    if not isinstance(label, dict):
        return ('official_parser', 'invalid-shape', repr(label))
    penalties = tuple(sorted(
        (penalty.get('type'), penalty.get('magnitude'))
        for penalty in label.get('penalties', [])))
    return (
        'official_parser', label.get('verdict'),
        tuple(sorted(label.get('cited_articles', []))), penalties)


def _cohen_kappa(pairs):
    if not pairs:
        return None
    left = Counter(a for a, _ in pairs)
    right = Counter(b for _, b in pairs)
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    expected = sum(left[label] * right[label] for label in set(left) | set(right)) / (n * n)
    if expected == 1:
        return 1.0 if observed == 1 else None
    return (observed - expected) / (1 - expected)


def score_validation_records(records):
    summary = {
        'total': 0,
        'resolved': 0,
        'dual_annotated': 0,
        'annotator_agreements': 0,
        'annotator_disagreements': 0,
        'official_verdict_exact': 0,
        'official_articles_exact': 0,
        'official_penalty_types_exact': 0,
        'official_n': 0,
        'reporter_type_exact': 0,
        'reporter_n': 0,
        'reporter_confusion': Counter(),
    }
    annotation_pairs = []
    for record in records:
        summary['total'] += 1
        a, b = record.get('annotator_a'), record.get('annotator_b')
        if a is not None and b is not None:
            pair = (
                _annotation_category(record, a),
                _annotation_category(record, b))
            annotation_pairs.append(pair)
            summary['dual_annotated'] += 1
            if pair[0] == pair[1]:
                summary['annotator_agreements'] += 1
            else:
                summary['annotator_disagreements'] += 1
        human, _ = resolved_human_label(record)
        if human is None:
            continue
        summary['resolved'] += 1
        machine = record.get('machine_label')
        if record['task'] == 'reporter_type':
            summary['reporter_n'] += 1
            summary['reporter_type_exact'] += machine == human
            summary['reporter_confusion'][(human, machine)] += 1
        elif record['task'] == 'official_parser':
            summary['official_n'] += 1
            summary['official_verdict_exact'] += (
                machine.get('verdict') == human.get('verdict'))
            summary['official_articles_exact'] += _set_equal(
                machine.get('cited_articles'), human.get('cited_articles'))
            machine_penalties = {p['type'] for p in machine.get('penalties', [])}
            human_penalties = {p['type'] for p in human.get('penalties', [])}
            summary['official_penalty_types_exact'] += (
                machine_penalties == human_penalties)
    summary['annotator_agreement_rate'] = (
        summary['annotator_agreements'] / summary['dual_annotated']
        if summary['dual_annotated'] else None)
    summary['cohen_kappa'] = _cohen_kappa(annotation_pairs)
    return summary


def render_validation_report(summary):
    def ratio(value, denominator):
        return f'{value / denominator:.1%}' if denominator else 'n/a'

    lines = [
        '# Human validation report', '',
        f"- tasks: {summary['total']}",
        f"- resolved by agreement/adjudication: {summary['resolved']}",
        f"- dual-annotated: {summary['dual_annotated']}",
        '- raw annotator agreement: ' + (
            f"{summary['annotator_agreement_rate']:.1%}"
            if summary['annotator_agreement_rate'] is not None else 'n/a'),
        '- Cohen kappa (full task label): ' + (
            f"{summary['cohen_kappa']:.3f}"
            if summary['cohen_kappa'] is not None else 'n/a'),
        f"- annotator disagreements: {summary['annotator_disagreements']}",
        '', '## Official parser', '',
        f"- n: {summary['official_n']}",
        '- verdict exact: ' + ratio(
            summary['official_verdict_exact'], summary['official_n']),
        '- cited articles exact: ' + ratio(
            summary['official_articles_exact'], summary['official_n']),
        '- penalty types exact: ' + ratio(
            summary['official_penalty_types_exact'], summary['official_n']),
        '', '## Reporter type heuristic', '',
        f"- n: {summary['reporter_n']}",
        '- exact accuracy: ' + ratio(
            summary['reporter_type_exact'], summary['reporter_n']),
        '- confusion (human -> machine):',
    ]
    for (human, machine), count in summary['reporter_confusion'].most_common():
        lines.append(f'  - {human} -> {machine}: {count}')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    sample_parser = subparsers.add_parser('sample')
    sample_parser.add_argument('dump')
    sample_parser.add_argument('out')
    sample_parser.add_argument('--per-stratum', type=int, default=25)
    sample_parser.add_argument('--seed', type=int, default=42)
    score_parser = subparsers.add_parser('score')
    score_parser.add_argument('annotations')
    score_parser.add_argument('--out')
    args = parser.parse_args(argv)

    if args.command == 'sample':
        records = build_validation_records(
            iter_complaints(args.dump), args.per_stratum, args.seed)
        with open(args.out, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f'{len(records)} restricted annotation tasks -> {args.out}')
    else:
        with open(args.annotations, encoding='utf-8') as f:
            records = [json.loads(line) for line in f if line.strip()]
        report = render_validation_report(score_validation_records(records))
        print(report, end='')
        if args.out:
            with open(args.out, 'w', encoding='utf-8') as f:
                f.write(report)


if __name__ == '__main__':
    main()
