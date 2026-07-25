"""Descriptive statistics over a complaint dump (direction B groundwork).

Usage:
    python -m analysis.stats data/complaints.jsonl [--markdown report.md]

Prints distributions of verdicts, cited articles, penalties, reporter types,
and evidence usage in report statements.
"""

import argparse
import sys
from collections import Counter

from analysis.load import iter_complaints
from analysis.official_parser import parse_official
from analysis.reporter_features import extract_complaint_reporter_features


def collect_stats(complaints):
    stats = {
        'n_complaints': 0,
        'verdicts': Counter(),
        'cited_documents': Counter(),
        'cited_articles': Counter(),
        'penalty_types': Counter(),
        'credit_points': Counter(),
        'mute_days': Counter(),
        'reporter_types': Counter(),
        'reporter_genders': Counter(),
        'n_reports': 0,
        'n_reports_with_statement': 0,
        'n_reports_missing_statement': 0,
        'n_reports_with_evidence_url': 0,
        'n_reports_with_debunk_hashtag': 0,
        'n_report_times_missing': 0,
        'actual_reporter_counts': Counter(),
        'serial_reporters': Counter(),
        'reporter_labels': {},
        'identity_sources': Counter(),
        'rumorer_names': Counter(),
        'report_years': Counter(),
    }
    for c in complaints:
        stats['n_complaints'] += 1

        official = parse_official((c.get('official') or {}).get('official_text'))
        stats['verdicts'][official['verdict'] or 'unparsed'] += 1
        for d in official['cited_documents']:
            stats['cited_documents'][d] += 1
        for a in official['cited_articles']:
            stats['cited_articles'][a] += 1
        for p in official['penalties']:
            stats['penalty_types'][p['type']] += 1
            if p['type'] == 'credit_deduction':
                stats['credit_points'][p['magnitude']] += 1
            elif p['type'] == 'mute':
                stats['mute_days'][p['magnitude'] if p['magnitude'] is not None else 'permanent'] += 1

        seen_reporter_keys = set()
        for r in extract_complaint_reporter_features(c):
            stats['n_reports'] += 1
            stats['reporter_types'][r['reporter_type']] += 1
            stats['reporter_genders'][r['reporter_gender'] or 'unknown'] += 1
            stats['identity_sources'][r['identity_source']] += 1
            if r['has_statement']:
                stats['n_reports_with_statement'] += 1
                stats['n_reports_with_evidence_url'] += r['has_evidence_url']
                stats['n_reports_with_debunk_hashtag'] += r['uses_debunk_hashtag']
            else:
                stats['n_reports_missing_statement'] += 1
            if (r['reporter_key']
                    and r['reporter_key'] not in seen_reporter_keys):
                seen_reporter_keys.add(r['reporter_key'])
                stats['serial_reporters'][r['reporter_key']] += 1
                if r['reporter_name']:
                    stats['reporter_labels'].setdefault(
                        r['reporter_key'], Counter())[r['reporter_name']] += 1
            if r['report_time']:
                stats['report_years'][r['report_time'][:4]] += 1
            else:
                stats['n_report_times_missing'] += 1

        count = c.get('actual_reporter_count')
        if isinstance(count, int):
            stats['actual_reporter_counts'][count] += 1
        rumorer = (c.get('rumor') or {}).get('rumorer_name')
        if rumorer:
            stats['rumorer_names'][rumorer] += 1

    return stats


def _fmt_counter(counter, top=15):
    total = sum(counter.values()) or 1
    lines = []
    for key, n in counter.most_common(top):
        lines.append(f'  {key}: {n} ({n / total:.1%})')
    return '\n'.join(lines) or '  (empty)'


def render_report(stats):
    statement_ratio = (lambda n: f'{n} ({n / (stats["n_reports_with_statement"] or 1):.1%})')
    top_serial = []
    for key, n in stats['serial_reporters'].most_common(10):
        if n <= 1:
            continue
        labels = stats['reporter_labels'].get(key)
        label = labels.most_common(1)[0][0] if labels else key
        top_serial.append(f'  {label} [{key}]: {n} visible cases')
    top_rumorers = [f'  {name}: {n} cases' for name, n in stats['rumorer_names'].most_common(10) if n > 1]
    return '\n'.join([
        f'# Complaint dump statistics',
        f'',
        f'Complaints: {stats["n_complaints"]}, report statements: {stats["n_reports"]}',
        f'',
        f'## Report years (known timestamps only)', _fmt_counter(stats['report_years']),
        f'  missing report timestamps: {stats["n_report_times_missing"]}',
        f'',
        f'## Verdicts', _fmt_counter(stats['verdicts']),
        f'',
        f'## Cited rulebooks', _fmt_counter(stats['cited_documents']),
        f'',
        f'## Cited rule articles (第N条)', _fmt_counter(stats['cited_articles']),
        f'',
        f'## Penalty types', _fmt_counter(stats['penalty_types']),
        f'',
        f'## Credit points deducted', _fmt_counter(stats['credit_points']),
        f'',
        f'## Mute durations (days)', _fmt_counter(stats['mute_days']),
        f'',
        f'## Reporter account types', _fmt_counter(stats['reporter_types']),
        f'',
        f'## Reporter genders', _fmt_counter(stats['reporter_genders']),
        f'',
        f'## Reporter identity source', _fmt_counter(stats['identity_sources']),
        f'',
        f'## Report statements',
        f'  present: {stats["n_reports_with_statement"]}',
        f'  missing: {stats["n_reports_missing_statement"]}',
        f'  with URL among present: {statement_ratio(stats["n_reports_with_evidence_url"])}',
        f'  with #微博辟谣# among present: {statement_ratio(stats["n_reports_with_debunk_hashtag"])}',
        f'',
        f'## Reporters per case (actual_reporter_count)', _fmt_counter(stats['actual_reporter_counts']),
        f'',
        f'## Serial reporters (>1 case, top 10)', '\n'.join(top_serial) or '  (none)',
        f'',
        f'## Repeat rumorers (>1 case, top 10)', '\n'.join(top_rumorers) or '  (none)',
        f'',
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', help='mongoexport .jsonl / .json file')
    parser.add_argument('--markdown', help='also write the report to this file')
    args = parser.parse_args(argv)

    report = render_report(collect_stats(iter_complaints(args.dump)))
    sys.stdout.write(report)
    if args.markdown:
        with open(args.markdown, 'w', encoding='utf-8') as f:
            f.write(report)


if __name__ == '__main__':
    main()
