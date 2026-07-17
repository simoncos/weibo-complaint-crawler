"""Case-study profiles of the top serial reporters (direction B).

For each of the top-N reporters by case count: activity span, account type,
statement style (length, evidence links, #微博辟谣#), reporting latency
(rumor post time -> report time), most-targeted rumorers, sample statements.

Usage:
    python -m analysis.reporter_profiles dump.json --top 10 [--out profiles.md]
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime

from analysis.load import iter_complaints
from analysis.reporter_features import extract_report_features


def _parse_dt(s):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def collect_profiles(complaints):
    profiles = defaultdict(lambda: {
        'cases': 0, 'years': Counter(), 'types': Counter(),
        'evidence': 0, 'hashtag': 0, 'lengths': [], 'latencies_h': [],
        'targets': Counter(), 'samples': [],
    })
    for c in complaints:
        rumor = c.get('rumor') or {}
        rumor_dt = _parse_dt(rumor.get('rumor_time') or '')
        for raw in c.get('reports') or []:
            r = extract_report_features(raw)
            name = r['reporter_name']
            if not name:
                continue
            p = profiles[name]
            p['cases'] += 1
            p['types'][r['reporter_type']] += 1
            if r['report_time']:
                p['years'][r['report_time'][:4]] += 1
                report_dt = _parse_dt(r['report_time'])
                if rumor_dt and report_dt and report_dt >= rumor_dt:
                    p['latencies_h'].append((report_dt - rumor_dt).total_seconds() / 3600)
            p['evidence'] += r['has_evidence_url']
            p['hashtag'] += r['uses_debunk_hashtag']
            if r['statement']:
                p['lengths'].append(r['statement_length'])
                if len(p['samples']) < 3:
                    p['samples'].append(r['statement'][:120])
            if rumor.get('rumorer_name'):
                p['targets'][rumor['rumorer_name']] += 1
    return profiles


def _median(values):
    if not values:
        return None
    values = sorted(values)
    return values[len(values) // 2]


def render_profile(name, p):
    years = ', '.join(f'{y}:{n}' for y, n in sorted(p['years'].items()))
    latency = _median(p['latencies_h'])
    top_targets = ', '.join(f'{t}({n})' for t, n in p['targets'].most_common(3))
    lines = [
        f'### {name}',
        '',
        f'- cases: {p["cases"]}, active years: {years}',
        f'- account type: {p["types"].most_common(1)[0][0]}',
        f'- evidence-URL rate: {p["evidence"] / p["cases"]:.1%}, '
        f'#微博辟谣# rate: {p["hashtag"] / p["cases"]:.1%}, '
        f'median statement length: {_median(p["lengths"]) or 0} chars',
        f'- median latency rumor->report: '
        + (f'{latency:.1f} h' if latency is not None else 'n/a'),
        f'- top targets: {top_targets or "n/a"}',
        f'- sample statements:',
    ]
    lines += [f'  - {s}' for s in p['samples']]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump')
    parser.add_argument('--top', type=int, default=10)
    parser.add_argument('--out', help='write markdown here as well')
    args = parser.parse_args(argv)

    profiles = collect_profiles(iter_complaints(args.dump))
    ranked = sorted(profiles.items(), key=lambda kv: kv[1]['cases'], reverse=True)
    report = '# Top serial reporter profiles\n\n' + '\n\n'.join(
        render_profile(name, p) for name, p in ranked[:args.top]) + '\n'
    sys.stdout.write(report)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(report)


if __name__ == '__main__':
    main()
