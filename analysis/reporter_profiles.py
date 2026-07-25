"""Profiles of repeatedly visible reporter identities.

Profiles are keyed by numeric platform UID when available and explicitly report
missing-time denominators. They describe public-page visibility, not all people
who submitted reports.
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime

from analysis.load import iter_complaints
from analysis.reporter_features import extract_report_features


def _parse_dt(value):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def median(values):
    if not values:
        return None
    values = sorted(values)
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def collect_profiles(complaints):
    profiles = defaultdict(lambda: {
        'visible_cases': 0,
        'names': Counter(),
        'identity_sources': Counter(),
        'years': Counter(),
        'types': Counter(),
        'evidence': 0,
        'statements_present': 0,
        'missing_statements': 0,
        'hashtag': 0,
        'lengths': [],
        'latencies_h': [],
        'report_time_known': 0,
        'report_time_missing': 0,
        'targets': Counter(),
        'samples': [],
    })
    for complaint in complaints:
        rumor = complaint.get('rumor') or {}
        rumor_dt = _parse_dt(rumor.get('rumor_time') or '')
        seen = set()
        for raw in complaint.get('reports') or []:
            reporter = extract_report_features(raw)
            key = reporter['reporter_key']
            if not key or key in seen:
                continue
            seen.add(key)
            profile = profiles[key]
            profile['visible_cases'] += 1
            profile['identity_sources'][reporter['identity_source']] += 1
            if reporter['reporter_name']:
                profile['names'][reporter['reporter_name']] += 1
            profile['types'][reporter['reporter_type']] += 1

            report_dt = _parse_dt(reporter['report_time'] or '')
            if report_dt:
                profile['report_time_known'] += 1
                profile['years'][str(report_dt.year)] += 1
                if rumor_dt and report_dt >= rumor_dt:
                    profile['latencies_h'].append(
                        (report_dt - rumor_dt).total_seconds() / 3600)
            else:
                profile['report_time_missing'] += 1

            if reporter['has_statement']:
                profile['statements_present'] += 1
                profile['evidence'] += reporter['has_evidence_url']
                profile['hashtag'] += reporter['uses_debunk_hashtag']
                profile['lengths'].append(reporter['statement_length'])
                if len(profile['samples']) < 3:
                    profile['samples'].append(reporter['statement'][:120])
            else:
                profile['missing_statements'] += 1
            if rumor.get('rumorer_name'):
                profile['targets'][rumor['rumorer_name']] += 1
    return profiles


def render_profile(key, profile):
    display_name = profile['names'].most_common(1)[0][0] if profile['names'] else key
    years = ', '.join(f'{year}:{n}' for year, n in sorted(profile['years'].items()))
    latency = median(profile['latencies_h'])
    top_targets = ', '.join(
        f'{target}({n})' for target, n in profile['targets'].most_common(3))
    statement_n = profile['statements_present']
    lines = [
        f'### {display_name}', '',
        f'- internal identity key: `{key}`',
        f'- visible cases: {profile["visible_cases"]}; active years with known '
        f'timestamps: {years or "none"}',
        f'- report time known/missing: {profile["report_time_known"]} / '
        f'{profile["report_time_missing"]}',
        f'- latency effective n: {len(profile["latencies_h"])}',
        f'- account type (heuristic): '
        f'{profile["types"].most_common(1)[0][0]}',
        f'- statements present/missing: {statement_n} / '
        f'{profile["missing_statements"]}',
        f'- URL-presence rate among present statements: '
        f'{profile["evidence"] / (statement_n or 1):.1%}',
        f'- #微博辟谣# rate among present statements: '
        f'{profile["hashtag"] / (statement_n or 1):.1%}',
        f'- median statement length: {median(profile["lengths"]) or 0} chars',
        '- median latency rumor->report: '
        + (f'{latency:.1f} h' if latency is not None else 'n/a'),
        f'- top visible targets: {top_targets or "n/a"}',
        '- sample statements (restricted output; do not publish without review):',
    ]
    lines += [f'  - {sample}' for sample in profile['samples']]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump')
    parser.add_argument('--top', type=int, default=10)
    parser.add_argument('--out', help='write markdown here as well')
    args = parser.parse_args(argv)

    profiles = collect_profiles(iter_complaints(args.dump))
    ranked = sorted(
        profiles.items(), key=lambda item: item[1]['visible_cases'], reverse=True)
    report = '# Top visible reporter profiles\n\n' + '\n\n'.join(
        render_profile(key, profile) for key, profile in ranked[:args.top]) + '\n'
    sys.stdout.write(report)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(report)


if __name__ == '__main__':
    main()
