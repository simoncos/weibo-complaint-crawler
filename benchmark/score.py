"""Score adjudication predictions against gold labels.

Predictions file: JSONL with {case_index or case_id, verdict, cited_articles,
penalties:[{type, magnitude}]}. Works for LLM outputs and human baselines alike.

Usage:
    python -m benchmark.score instances.jsonl predictions.jsonl
"""

import argparse
import json
from collections import Counter


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 1.0


def _credit(penalties):
    for p in penalties:
        if (p.get('type') if isinstance(p, dict) else p) == 'credit_deduction':
            return p.get('magnitude')
    return None


def score_pair(gold, pred):
    gold_types = [p['type'] for p in gold['penalties']]
    pred_types = [p['type'] for p in pred.get('penalties', [])]
    gold_credit, pred_credit = _credit(gold['penalties']), _credit(pred.get('penalties', []))
    return {
        'verdict_match': pred.get('verdict') == gold['verdict'],
        'articles_exact': set(pred.get('cited_articles', [])) == set(gold['cited_articles']),
        'articles_jaccard': jaccard(pred.get('cited_articles', []), gold['cited_articles']),
        'penalty_types_jaccard': jaccard(pred_types, gold_types),
        'credit_exact': (gold_credit == pred_credit),
        'credit_abs_err': (abs(gold_credit - pred_credit)
                           if gold_credit is not None and pred_credit is not None else None),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('instances')
    parser.add_argument('predictions')
    args = parser.parse_args(argv)

    with open(args.instances, encoding='utf-8') as f:
        instances = [json.loads(line) for line in f]
    by_id = {inst['case_id']: inst for inst in instances}

    totals, credit_errs, n = Counter(), [], 0
    confusion = Counter()
    with open(args.predictions, encoding='utf-8') as f:
        for line in f:
            pred = json.loads(line)
            if pred.get('case_id') in by_id:
                inst = by_id[pred['case_id']]
            elif 'case_index' in pred:
                inst = instances[pred['case_index']]
            else:
                continue
            result = score_pair(inst['gold'], pred)
            n += 1
            confusion[(inst['gold']['verdict'], pred.get('verdict'))] += 1
            for key in ('verdict_match', 'articles_exact', 'articles_jaccard',
                        'penalty_types_jaccard', 'credit_exact'):
                totals[key] += float(result[key])
            if result['credit_abs_err'] is not None:
                credit_errs.append(result['credit_abs_err'])

    print(f'cases scored: {n}')
    for key, value in totals.items():
        print(f'{key}: {value / (n or 1):.3f}')
    if credit_errs:
        print(f'credit_MAE (both sides deducted): {sum(credit_errs) / len(credit_errs):.2f} '
              f'(n={len(credit_errs)})')
    print('\nverdict confusion (gold, pred): count')
    for (g, p), c in confusion.most_common():
        print(f'  ({g}, {p}): {c}')


if __name__ == '__main__':
    main()
