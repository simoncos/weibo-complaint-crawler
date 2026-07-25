"""Concentration and temporal summaries for visible complaint reporters.

The public case page exposes at most 20 reporter profiles. Consequently this
module estimates activity among *visible reporter rows*, not all people who
reported a case. It reports truncation and a complete-case sensitivity subset
instead of silently treating visible rows as the full population.
"""

import argparse
import os
import sys
from collections import Counter, defaultdict

from analysis.load import iter_complaints
from analysis.official_parser import parse_official
from analysis.reporter_features import extract_complaint_reporter_features


def gini(counts):
    values = sorted(counts)
    n = len(values)
    total = sum(values)
    if n == 0 or total == 0:
        return 0.0
    cumulative_sum = 0
    weighted = 0
    for value in values:
        cumulative_sum += value
        weighted += cumulative_sum
    return 1 - (2 * weighted - total) / (n * total)


def lorenz_points(counts, steps=100):
    values = sorted(counts)
    total = sum(values) or 1
    n = len(values) or 1
    points, cumulative = [(0.0, 0.0)], 0
    for i, value in enumerate(values, 1):
        cumulative += value
        if i % max(1, n // steps) == 0 or i == n:
            points.append((i / n, cumulative / total))
    return points


def top_k_share(counter, ks=(1, 10, 100)):
    total = sum(counter.values()) or 1
    ordered = [n for _, n in counter.most_common()]
    return {k: sum(ordered[:k]) / total for k in ks}


def _year(value):
    value = (value or '').strip()
    return value[:4] if len(value) >= 4 and value[:4].isdigit() else None


def _case_year(complaint, reporters):
    rumor_year = _year((complaint.get('rumor') or {}).get('rumor_time'))
    if rumor_year:
        return rumor_year, 'rumor_time'
    report_times = sorted(
        r['report_time'] for r in reporters if r.get('report_time'))
    if report_times:
        return _year(report_times[0]), 'earliest_report_time'
    return None, 'missing'


def _visibility_status(actual, visible):
    if not isinstance(actual, int):
        return 'unknown'
    if actual == visible:
        return 'complete'
    if actual > visible:
        return 'truncated'
    return 'inconsistent'


def collect(complaints):
    data = {
        'reporter_cases': Counter(),
        'complete_reporter_cases': Counter(),
        'reporter_labels': defaultdict(Counter),
        'identity_sources': Counter(),
        'case_visibility': Counter(),
        'visible_reporter_rows': 0,
        'known_actual_reporters': 0,
        'hidden_reporters_lower_bound': 0,
        'case_years': Counter(),
        'case_year_sources': Counter(),
        'report_time_coverage': Counter(),
        'type_year': defaultdict(Counter),
        'complete_type_year': defaultdict(Counter),
        'penalty_year': defaultdict(Counter),
        'credit_year': defaultdict(Counter),
        'rulebook_year': defaultdict(Counter),
        'evidence_year': defaultdict(Counter),
        'complete_evidence_year': defaultdict(Counter),
    }
    for complaint in complaints:
        official = parse_official(
            (complaint.get('official') or {}).get('official_text'))
        reporters = extract_complaint_reporter_features(complaint)
        visible = len(reporters)
        actual = complaint.get('actual_reporter_count')
        visibility = _visibility_status(actual, visible)
        data['case_visibility'][visibility] += 1
        data['visible_reporter_rows'] += visible
        if isinstance(actual, int):
            data['known_actual_reporters'] += actual
            data['hidden_reporters_lower_bound'] += max(0, actual - visible)

        case_year, year_source = _case_year(complaint, reporters)
        data['case_year_sources'][year_source] += 1
        if case_year:
            data['case_years'][case_year] += 1

        seen_keys = set()
        for row_index, reporter in enumerate(reporters):
            key = reporter['reporter_key']
            dedupe_key = key or f'missing:{row_index}'
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            data['identity_sources'][reporter['identity_source']] += 1
            if key:
                data['reporter_cases'][key] += 1
                if visibility == 'complete':
                    data['complete_reporter_cases'][key] += 1
                if reporter['reporter_name']:
                    data['reporter_labels'][key][reporter['reporter_name']] += 1

            report_year = _year(reporter['report_time'])
            data['report_time_coverage'][
                'known' if report_year else 'missing'] += 1
            year = report_year or case_year
            if not year:
                continue
            data['type_year'][year][reporter['reporter_type']] += 1
            if visibility == 'complete':
                data['complete_type_year'][year][reporter['reporter_type']] += 1

            evidence = data['evidence_year'][year]
            complete_evidence = data['complete_evidence_year'][year]
            if reporter['has_statement']:
                evidence['statements'] += 1
                evidence['with_url'] += reporter['has_evidence_url']
                if visibility == 'complete':
                    complete_evidence['statements'] += 1
                    complete_evidence['with_url'] += reporter['has_evidence_url']
            else:
                evidence['missing_statement'] += 1
                if visibility == 'complete':
                    complete_evidence['missing_statement'] += 1

        if case_year:
            for penalty_type in {p['type'] for p in official['penalties']}:
                data['penalty_year'][case_year][penalty_type] += 1
            for magnitude in {
                    p['magnitude'] for p in official['penalties']
                    if p['type'] == 'credit_deduction'}:
                data['credit_year'][case_year][magnitude] += 1
            for document in set(official['cited_documents']):
                data['rulebook_year'][case_year][document] += 1
    return data


def _crosstab_md(year_counter, title, top_cols=8):
    columns = Counter()
    for counts in year_counter.values():
        columns.update(counts)
    columns = [column for column, _ in columns.most_common(top_cols)]
    lines = [
        f'## {title}', '',
        '| year | ' + ' | '.join(str(c) for c in columns) + ' |',
        '|' + '---|' * (len(columns) + 1),
    ]
    for year in sorted(year_counter):
        row = year_counter[year]
        lines.append(
            f'| {year} | ' + ' | '.join(str(row.get(c, 0)) for c in columns) + ' |')
    return '\n'.join(lines)


def _case_rate_md(year_counter, case_years, title, top_cols=8):
    columns = Counter()
    for counts in year_counter.values():
        columns.update(counts)
    columns = [column for column, _ in columns.most_common(top_cols)]
    lines = [
        f'## {title}', '',
        '| year | ' + ' | '.join(str(c) for c in columns) + ' | all cases |',
        '|' + '---|' * (len(columns) + 2),
    ]
    for year in sorted(case_years):
        denominator = case_years[year]
        row = year_counter.get(year, {})
        values = [
            f'{row.get(column, 0)} ({row.get(column, 0) / (denominator or 1):.1%})'
            for column in columns
        ]
        lines.append(
            f'| {year} | ' + ' | '.join(values) + f' | {denominator} |')
    return '\n'.join(lines)


def _concentration_md(counter, title):
    counts = list(counter.values())
    shares = top_k_share(counter)
    n_reporters = len(counts)
    appearances = sum(counts)
    one_case = sum(1 for value in counts if value == 1)
    return '\n'.join([
        f'## {title}', '',
        f'- resolved reporter identities: {n_reporters}',
        f'- visible case-appearances after within-case deduplication: {appearances}',
        f'- Gini coefficient: **{gini(counts):.3f}**',
        f'- top 1 share: **{shares[1]:.1%}**; top 10: **{shares[10]:.1%}**; '
        f'top 100: **{shares[100]:.1%}**',
        f'- identities appearing in one visible case: {one_case} '
        f'({one_case / (n_reporters or 1):.1%})',
    ])


def _evidence_md(counter, title):
    lines = [
        f'## {title}', '',
        '| year | statements present | with URL | URL rate among present | missing statement |',
        '|---|---|---|---|---|',
    ]
    for year in sorted(counter):
        row = counter[year]
        present = row['statements']
        rate = row['with_url'] / (present or 1)
        lines.append(
            f"| {year} | {present} | {row['with_url']} | {rate:.1%} | "
            f"{row['missing_statement']} |")
    return '\n'.join(lines)


def render(data):
    visibility = data['case_visibility']
    time_coverage = data['report_time_coverage']
    return '\n\n'.join([
        '# Visible-reporter concentration & temporal analysis',
        '\n'.join([
            '## Estimand and observation coverage', '',
            'All reporter metrics describe profiles visible on public case pages; '
            'they do not estimate every person who submitted a report.',
            f"- cases confirmed complete: {visibility['complete']}",
            f"- cases truncated by actual_reporter_count: {visibility['truncated']}",
            f"- cases with unknown completeness: {visibility['unknown']}",
            f"- inconsistent actual/visible counts: {visibility['inconsistent']}",
            f"- visible reporter rows: {data['visible_reporter_rows']}",
            f"- known actual reporter total: {data['known_actual_reporters']}",
            f"- lower bound on hidden reporter rows: {data['hidden_reporters_lower_bound']}",
            f"- reporter times known/missing: {time_coverage['known']} / "
            f"{time_coverage['missing']}",
            f"- identity source counts: {dict(data['identity_sources'])}",
            f"- case-year proxy sources: {dict(data['case_year_sources'])}",
        ]),
        _concentration_md(data['reporter_cases'],
                          'All visible cases: reporter concentration'),
        _concentration_md(data['complete_reporter_cases'],
                          'Confirmed-complete cases: sensitivity analysis'),
        _crosstab_md(data['type_year'],
                     'Reporter type x year (visible profiles; case-year fallback)'),
        _crosstab_md(data['complete_type_year'],
                     'Reporter type x year (confirmed-complete cases)'),
        _case_rate_md(data['penalty_year'], data['case_years'],
                      'Penalty type x case-year proxy (case prevalence)'),
        _crosstab_md(data['credit_year'], 'Credit points x case-year proxy'),
        _case_rate_md(data['rulebook_year'], data['case_years'],
                      'Cited rulebook x case-year proxy', top_cols=6),
        _evidence_md(data['evidence_year'],
                     'URL presence among non-missing statements'),
        _evidence_md(data['complete_evidence_year'],
                     'URL presence: confirmed-complete-case sensitivity'),
        '',
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump')
    parser.add_argument('--out-dir', help='write report and Lorenz data here')
    args = parser.parse_args(argv)

    data = collect(iter_complaints(args.dump))
    report = render(data)
    sys.stdout.write(report)
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        with open(os.path.join(args.out_dir, 'concentration.md'), 'w', encoding='utf-8') as f:
            f.write(report)
        with open(os.path.join(args.out_dir, 'lorenz.csv'), 'w', encoding='utf-8') as f:
            f.write('subset,population_share,activity_share\n')
            for subset, counter in (
                    ('visible', data['reporter_cases']),
                    ('confirmed_complete', data['complete_reporter_cases'])):
                for x, y in lorenz_points(list(counter.values())):
                    f.write(f'{subset},{x:.6f},{y:.6f}\n')


if __name__ == '__main__':
    main()
