"""Build the LLM-adjudication benchmark (direction A) from a complaint dump.

Each benchmark instance pairs the case materials (rumor + reporter statements,
i.e. what a human adjudicator saw) with the gold labels parsed from the
platform's own verdict text. PII is reduced: user URLs / avatars are dropped
and account names are replaced with stable pseudonyms.

Usage:
    python -m benchmark.build_benchmark data/complaints.jsonl benchmark/instances.jsonl
"""

import argparse
import hashlib
import json

from analysis.load import iter_complaints
from analysis.official_parser import parse_official
from analysis.reporter_features import extract_report_features


def _pseudonym(name, role):
    digest = hashlib.sha256(('weibo-cmc:' + (name or '')).encode('utf-8')).hexdigest()[:8]
    return f'{role}_{digest}'


def build_instance(complaint):
    """Return one benchmark instance dict, or None if labels are unusable."""
    official_text = (complaint.get('official') or {}).get('official_text')
    gold = parse_official(official_text)
    rumor = complaint.get('rumor') or {}
    rumor_text = rumor.get('rumor_text')
    if not rumor_text or gold['verdict'] is None:
        return None
    # The eval is 3-way; informal falsity rulings count as upheld, and the rare
    # “有害信息” rulings are a different offense — excluded from this benchmark.
    verdict = {'upheld_informal': 'upheld'}.get(gold['verdict'], gold['verdict'])
    if verdict not in ('upheld', 'rejected', 'undetermined'):
        return None

    rumorer_alias = _pseudonym(rumor.get('rumorer_name'), 'user')
    reports = []
    for r in complaint.get('reports') or []:
        feats = extract_report_features(r)
        if not feats['statement']:
            continue
        reports.append({
            'reporter_alias': _pseudonym(feats['reporter_name'], 'reporter'),
            'reporter_type': feats['reporter_type'],
            'report_time': feats['report_time'],
            'statement': feats['statement'],
        })

    return {
        'case_id': complaint.get('url'),
        'input': {
            # Rumorer name is stripped from the scraped text prefix as well.
            'reported_post': rumor_text.split('：', 1)[-1].strip(),
            'reported_user': {
                'alias': rumorer_alias,
                'gender': rumor.get('rumorer_gender'),
                'location': rumor.get('rumorer_location'),
                'description': rumor.get('rumorer_description'),
            },
            'post_time': rumor.get('rumor_time'),
            'reports': reports,
            'reporter_count': complaint.get('actual_reporter_count'),
        },
        'gold': {
            'verdict': verdict,
            'cited_articles': gold['cited_articles'],
            'penalties': gold['penalties'],
        },
        # Kept for error analysis; drop before public release.
        'official_text': official_text,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', help='mongoexport .jsonl / .json file')
    parser.add_argument('out', help='output benchmark .jsonl')
    parser.add_argument('--limit', type=int, help='max instances')
    args = parser.parse_args(argv)

    n_in = n_out = 0
    with open(args.out, 'w', encoding='utf-8') as f:
        for complaint in iter_complaints(args.dump):
            n_in += 1
            instance = build_instance(complaint)
            if instance:
                f.write(json.dumps(instance, ensure_ascii=False) + '\n')
                n_out += 1
                if args.limit and n_out >= args.limit:
                    break
    print(f'{n_out}/{n_in} complaints converted to benchmark instances -> {args.out}')


if __name__ == '__main__':
    main()
