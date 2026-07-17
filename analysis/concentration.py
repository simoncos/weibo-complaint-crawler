"""Concentration & temporal analysis (direction B core numbers).

Computes:
- reporter concentration: Gini coefficient, Lorenz curve points, top-K shares
- reporter-type x year timeline (who does the reporting over time)
- penalty x year crosstab (how sanctioning practice evolved)
- rulebook x year crosstab (the platform's "legislative" history)

Usage:
    python -m analysis.concentration dump.json --out-dir out/
Writes markdown tables to stdout (and --out-dir/concentration.md), plus
lorenz.csv with cumulative-share points for plotting.
"""

import argparse
import os
import sys
from collections import Counter, defaultdict

from analysis.load import iter_complaints
from analysis.official_parser import parse_official
from analysis.reporter_features import extract_complaint_reporter_features


def gini(counts):
    """Gini coefficient of a list of per-individual counts."""
    values = sorted(counts)
    n = len(values)
    total = sum(values)
    if n == 0 or total == 0:
        return 0.0
    cum = 0
    weighted = 0
    for i, v in enumerate(values, 1):
        cum += v
        weighted += cum
    # G = 1 - 2 * sum_i(cum_i) / (n * total) + 1/n  (trapezoid Lorenz form)
    return 1 - (2 * weighted - total) / (n * total)


def lorenz_points(counts, steps=100):
    """(population share, activity share) points of the Lorenz curve."""
    values = sorted(counts)
    total = sum(values) or 1
    n = len(values) or 1
    points, cum = [(0.0, 0.0)], 0
    for i, v in enumerate(values, 1):
        cum += v
        if i % max(1, n // steps) == 0 or i == n:
            points.append((i / n, cum / total))
    return points


def top_k_share(counter, ks=(1, 10, 100)):
    total = sum(counter.values()) or 1
    ordered = [n for _, n in counter.most_common()]
    return {k: sum(ordered[:k]) / total for k in ks}


def collect(complaints):
    data = {
        'reporter_cases': Counter(),          # reporter name -> #cases appeared in
        'type_year': defaultdict(Counter),    # year -> reporter type -> #statements
        'penalty_year': defaultdict(Counter),  # year -> penalty type -> #cases
        'credit_year': defaultdict(Counter),  # year -> points -> #cases
        'rulebook_year': defaultdict(Counter),  # year -> rulebook -> #cases
        'evidence_year': defaultdict(Counter),  # year -> has_url/total
    }
    for c in complaints:
        official = parse_official((c.get('official') or {}).get('official_text'))
        reporters = extract_complaint_reporter_features(c)

        # Case year: first report time, falling back to the rumor's post time
        # (reports whose statements were deleted carry no report_time).
        case_year = next((r['report_time'][:4] for r in reporters if r['report_time']),
                         ((c.get('rumor') or {}).get('rumor_time') or '')[:4] or None)
        for r in reporters:
            year = r['report_time'][:4] if r['report_time'] else case_year
            if year:
                data['type_year'][year][r['reporter_type']] += 1
                data['evidence_year'][year]['total'] += 1
                data['evidence_year'][year]['with_url'] += r['has_evidence_url']
            if r['reporter_name']:
                data['reporter_cases'][r['reporter_name']] += 1

        if case_year:
            for p in official['penalties']:
                data['penalty_year'][case_year][p['type']] += 1
                if p['type'] == 'credit_deduction':
                    data['credit_year'][case_year][p['magnitude']] += 1
            for d in official['cited_documents']:
                data['rulebook_year'][case_year][d] += 1
    return data


def _crosstab_md(year_counter, title, top_cols=8):
    cols = Counter()
    for counts in year_counter.values():
        cols.update(counts)
    cols = [c for c, _ in cols.most_common(top_cols)]
    lines = [f'## {title}', '', '| year | ' + ' | '.join(str(c) for c in cols) + ' | total |',
             '|' + '---|' * (len(cols) + 2)]
    for year in sorted(year_counter):
        row = year_counter[year]
        total = sum(row.values())
        lines.append(f'| {year} | ' + ' | '.join(str(row.get(c, 0)) for c in cols)
                     + f' | {total} |')
    return '\n'.join(lines)


def render(data):
    counts = list(data['reporter_cases'].values())
    shares = top_k_share(data['reporter_cases'])
    n_reporters = len(counts)
    total_appearances = sum(counts)
    one_case = sum(1 for v in counts if v == 1)

    evidence = ['## Evidence-link rate by year', '', '| year | with URL | total | rate |', '|---|---|---|---|']
    for year in sorted(data['evidence_year']):
        row = data['evidence_year'][year]
        rate = row['with_url'] / (row['total'] or 1)
        evidence.append(f"| {year} | {row['with_url']} | {row['total']} | {rate:.1%} |")

    return '\n\n'.join([
        '# Concentration & temporal analysis',
        '\n'.join([
            '## Reporter concentration',
            '',
            f'- unique reporters: {n_reporters}, case-appearances: {total_appearances}',
            f'- Gini coefficient: **{gini(counts):.3f}**',
            f'- top 1 reporter covers **{shares[1]:.1%}** of appearances, '
            f'top 10: **{shares[10]:.1%}**, top 100: **{shares[100]:.1%}**',
            f'- reporters with exactly one case: {one_case} ({one_case / (n_reporters or 1):.1%})',
        ]),
        _crosstab_md(data['type_year'], 'Reporter type x year (statements)'),
        _crosstab_md(data['penalty_year'], 'Penalty type x year (cases)'),
        _crosstab_md(data['credit_year'], 'Credit points deducted x year'),
        _crosstab_md(data['rulebook_year'], 'Cited rulebook x year', top_cols=6),
        '\n'.join(evidence),
        '',
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump')
    parser.add_argument('--out-dir', help='write concentration.md and lorenz.csv here')
    args = parser.parse_args(argv)

    data = collect(iter_complaints(args.dump))
    report = render(data)
    sys.stdout.write(report)

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        with open(os.path.join(args.out_dir, 'concentration.md'), 'w', encoding='utf-8') as f:
            f.write(report)
        with open(os.path.join(args.out_dir, 'lorenz.csv'), 'w', encoding='utf-8') as f:
            f.write('population_share,activity_share\n')
            for x, y in lorenz_points(list(data['reporter_cases'].values())):
                f.write(f'{x:.6f},{y:.6f}\n')


if __name__ == '__main__':
    main()
