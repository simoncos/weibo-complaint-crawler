"""Strictly score adjudication predictions against benchmark gold labels.

Accepted prediction records are either flat or the wrapped records emitted by
``benchmark.run_eval``::

    {"case_id": "...", "verdict": "upheld", ...}
    {"case_id": "...", "pred": {"verdict": "upheld", ...}, ...}

Unknown, duplicate and (by default) missing case IDs are errors rather than
silent exclusions.
"""

import argparse
import json
import math
from collections import Counter


VERDICTS = {'upheld', 'rejected', 'undetermined'}
PENALTY_TYPES = {
    'credit_deduction', 'mute', 'follow_ban', 'delete_post', 'account_closure'}


def jaccard(left, right):
    left, right = set(left), set(right)
    return len(left & right) / len(left | right) if (left | right) else 1.0


def _credit(penalties):
    for penalty in penalties:
        if penalty.get('type') == 'credit_deduction':
            return penalty.get('magnitude')
    return None


def _canonical_penalties(penalties):
    return {(p.get('type'), p.get('magnitude')) for p in penalties}


def normalize_prediction_record(record):
    prediction = record.get('pred') if isinstance(record.get('pred'), dict) else record
    case_id = record.get('case_id') or prediction.get('case_id')
    if not case_id:
        raise ValueError('prediction missing case_id')
    verdict = prediction.get('verdict')
    if verdict not in VERDICTS:
        raise ValueError(f'{case_id}: invalid verdict {verdict!r}')
    articles = prediction.get('cited_articles')
    if (not isinstance(articles, list)
            or not all(type(n) is int and n > 0 for n in articles)
            or len(articles) != len(set(articles))):
        raise ValueError(
            f'{case_id}: cited_articles must contain unique positive integers')
    penalties = prediction.get('penalties')
    if not isinstance(penalties, list):
        raise ValueError(f'{case_id}: penalties must be a list')
    seen_penalty_types = set()
    for penalty in penalties:
        if not isinstance(penalty, dict) or penalty.get('type') not in PENALTY_TYPES:
            raise ValueError(f'{case_id}: invalid penalty {penalty!r}')
        if penalty['type'] in seen_penalty_types:
            raise ValueError(
                f"{case_id}: duplicate penalty type {penalty['type']!r}")
        seen_penalty_types.add(penalty['type'])
        magnitude = penalty.get('magnitude')
        if magnitude is not None and (type(magnitude) is not int or magnitude < 0):
            raise ValueError(
                f'{case_id}: penalty magnitude must be non-negative int or null')
    return case_id, {
        'verdict': verdict,
        'cited_articles': articles,
        'penalties': penalties,
    }


def score_pair(gold, prediction):
    gold_types = {p['type'] for p in gold['penalties']}
    pred_types = {p['type'] for p in prediction.get('penalties', [])}
    gold_credit = _credit(gold['penalties'])
    pred_credit = _credit(prediction.get('penalties', []))
    both_credit = gold_credit is not None and pred_credit is not None
    return {
        'verdict_match': prediction.get('verdict') == gold['verdict'],
        'articles_exact': (
            set(prediction.get('cited_articles', [])) == set(gold['cited_articles'])),
        'articles_jaccard': jaccard(
            prediction.get('cited_articles', []), gold['cited_articles']),
        'penalty_types_jaccard': jaccard(pred_types, gold_types),
        'penalties_exact': (
            _canonical_penalties(prediction.get('penalties', []))
            == _canonical_penalties(gold['penalties'])),
        'credit_presence_exact': (
            (gold_credit is None) == (pred_credit is None)),
        'credit_magnitude_exact': (
            gold_credit == pred_credit if both_credit else None),
        'credit_abs_err': (
            abs(gold_credit - pred_credit) if both_credit else None),
    }


def score_records(instances, prediction_records, allow_partial=False):
    by_id = {}
    for instance in instances:
        case_id = instance.get('case_id')
        if not case_id or case_id in by_id:
            raise ValueError(f'duplicate or missing benchmark case_id: {case_id!r}')
        _, normalized_gold = normalize_prediction_record({
            'case_id': case_id, 'pred': instance.get('gold') or {}})
        by_id[case_id] = {**instance, 'gold': normalized_gold}
    if not by_id:
        raise ValueError('benchmark contains no instances')

    predictions = {}
    attempted = set()
    failures = Counter()
    for record in prediction_records:
        status = record.get('status')
        if status and status != 'success':
            case_id = record.get('case_id')
            if not case_id or case_id not in by_id:
                raise ValueError(f'unknown or missing result case_id: {case_id!r}')
            if case_id in attempted:
                raise ValueError(f'duplicate result case_id: {case_id}')
            attempted.add(case_id)
            failures[status] += 1
            continue
        case_id, prediction = normalize_prediction_record(record)
        if case_id not in by_id:
            raise ValueError(f'unknown prediction case_id: {case_id}')
        if case_id in attempted:
            raise ValueError(f'duplicate result case_id: {case_id}')
        attempted.add(case_id)
        predictions[case_id] = prediction

    missing = sorted(set(by_id) - attempted)
    if missing and not allow_partial:
        raise ValueError(
            f'missing {len(missing)} result records; '
            f'first missing case_id={missing[0]}')
    unscored = sorted(set(by_id) - set(predictions))

    totals = Counter()
    denominators = Counter()
    credit_errors = []
    confusion = Counter()
    era_verdict = Counter()
    per_case = []
    for case_id, prediction in predictions.items():
        gold = by_id[case_id]['gold']
        result = score_pair(gold, prediction)
        confusion[(gold['verdict'], prediction['verdict'])] += 1
        era = by_id[case_id].get('era', 'unknown')
        era_verdict[(era, result['verdict_match'])] += 1
        for key, value in result.items():
            if value is None:
                continue
            denominators[key] += 1
            if key == 'credit_abs_err':
                credit_errors.append(value)
            else:
                totals[key] += float(value)
        per_case.append({'case_id': case_id, 'score': result})
    gold_verdicts = Counter(instance['gold']['verdict'] for instance in by_id.values())
    majority_label, majority_count = gold_verdicts.most_common(1)[0]
    class_metrics = {}
    for label in sorted(VERDICTS):
        true_positive = confusion[(label, label)]
        predicted = sum(count for (gold, pred), count in confusion.items()
                        if pred == label)
        actual = sum(count for (gold, pred), count in confusion.items()
                     if gold == label)
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else None
        f1 = (2 * precision * recall / (precision + recall)
              if recall is not None and precision + recall else 0.0)
        class_metrics[label] = {
            'support': actual, 'precision': precision,
            'recall': recall, 'f1': f1,
        }
    supported = [metrics for metrics in class_metrics.values()
                 if metrics['support']]
    # The preregistered primary denominator is every frozen benchmark case.
    # Refusals, API errors and (when explicitly allowed) absent result records
    # therefore contribute zero rather than disappearing from the accuracy.
    verdict_matches = totals['verdict_match']
    verdict_n = len(by_id)
    if verdict_n:
        probability = verdict_matches / verdict_n
        z = 1.96
        denominator = 1 + z * z / verdict_n
        center = (probability + z * z / (2 * verdict_n)) / denominator
        margin = z * math.sqrt(
            probability * (1 - probability) / verdict_n
            + z * z / (4 * verdict_n * verdict_n)) / denominator
        verdict_wilson_95 = (center - margin, center + margin)
    else:
        verdict_wilson_95 = None
    return {
        'expected': len(by_id),
        'attempted': len(attempted),
        'scored': len(predictions),
        'missing': missing,
        'unscored': unscored,
        'failures': failures,
        'totals': totals,
        'denominators': denominators,
        'credit_errors': credit_errors,
        'confusion': confusion,
        'era_verdict': era_verdict,
        'majority_baseline': {
            'label': majority_label,
            'accuracy': majority_count / len(by_id),
        },
        'all_expected_rates': {
            key: totals[key] / len(by_id)
            for key in (
                'verdict_match', 'articles_exact', 'penalties_exact',
                'credit_presence_exact')
        },
        'class_metrics': class_metrics,
        'macro_f1_supported_classes': (
            sum(metrics['f1'] for metrics in supported) / len(supported)
            if supported else None),
        'balanced_accuracy_supported_classes': (
            sum(metrics['recall'] for metrics in supported) / len(supported)
            if supported else None),
        'verdict_wilson_95': verdict_wilson_95,
        'per_case': per_case,
    }


def render_score_report(summary):
    lines = [
        f"cases expected: {summary['expected']}",
        f"cases attempted: {summary['attempted']}",
        f"cases scored: {summary['scored']}",
        f"cases with no result record: {len(summary['missing'])}",
        f"cases unscored (failure or absent): {len(summary['unscored'])}",
        f"non-success statuses: {dict(summary['failures'])}",
        f"majority verdict baseline: {summary['majority_baseline']['label']} "
        f"({summary['majority_baseline']['accuracy']:.3f})",
        f"PRIMARY full-penalty exact (all expected cases): "
        f"{summary['all_expected_rates']['penalties_exact']:.3f}",
        f"failure-adjusted verdict agreement (all expected cases): "
        f"{summary['all_expected_rates']['verdict_match']:.3f}",
    ]
    for key in (
            'verdict_match', 'articles_exact', 'articles_jaccard',
            'penalty_types_jaccard', 'penalties_exact',
            'credit_presence_exact', 'credit_magnitude_exact'):
        denominator = summary['denominators'][key]
        if denominator:
            lines.append(f'{key} (successful responses): '
                         f'{summary["totals"][key] / denominator:.3f} '
                         f'(n={denominator})')
    lines.append(
        'failure-adjusted exact rates (all expected): '
        + ', '.join(
            f'{key}={value:.3f}'
            for key, value in summary['all_expected_rates'].items()))
    if summary['credit_errors']:
        errors = summary['credit_errors']
        lines.append(f'credit_MAE (both sides deducted): '
                     f'{sum(errors) / len(errors):.2f} (n={len(errors)})')
    if summary['verdict_wilson_95']:
        low, high = summary['verdict_wilson_95']
        lines.append(
            f'failure-adjusted verdict agreement Wilson 95% CI: '
            f'[{low:.3f}, {high:.3f}]')
    if summary['macro_f1_supported_classes'] is not None:
        lines.append(
            f"verdict macro F1 (successful responses; supported classes): "
            f"{summary['macro_f1_supported_classes']:.3f}")
        lines.append(
            f"verdict balanced accuracy (successful responses; supported classes): "
            f"{summary['balanced_accuracy_supported_classes']:.3f}")
    lines.extend(['', 'verdict confusion among successful responses (gold, pred): count'])
    for (gold, pred), count in summary['confusion'].most_common():
        lines.append(f'  ({gold}, {pred}): {count}')
    lines.extend(['', 'verdict accuracy by era among successful responses:'])
    eras = sorted({era for era, _ in summary['era_verdict']})
    for era in eras:
        correct = summary['era_verdict'][(era, True)]
        total = correct + summary['era_verdict'][(era, False)]
        lines.append(f'  {era}: {correct / (total or 1):.3f} (n={total})')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('instances')
    parser.add_argument('predictions')
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args(argv)

    with open(args.instances, encoding='utf-8') as f:
        instances = [json.loads(line) for line in f if line.strip()]
    with open(args.predictions, encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]
    summary = score_records(instances, records, args.allow_partial)
    print(render_score_report(summary), end='')


if __name__ == '__main__':
    main()
