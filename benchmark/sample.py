"""Stratified sampling of benchmark instances by rulebook generation.

The platform's rulebook changed three times over 2012-2018; sampling evenly
across generations lets the eval compare LLM agreement per "legal era".

Usage:
    python -m benchmark.sample instances.jsonl sample.jsonl --per-stratum 34 --seed 42
"""

import argparse
import json
import random

from analysis.official_parser import parse_cited_documents

# Rulebook title -> generation label
_GENERATIONS = {
    '新浪微博社区管理规定(试行)': 'gen1_sina_guiding',
    '新浪微博社区管理规定': 'gen1_sina_guiding',
    '微博社区管理规定(试行)': 'gen2_guiding',
    '微博社区管理规定': 'gen2_guiding',
    '微博举报投诉操作细则': 'gen3_xize',
}


def stratum_of(instance):
    docs = parse_cited_documents(instance.get('official_text') or '')
    for d in docs:
        if d in _GENERATIONS:
            return _GENERATIONS[d]
    return 'other'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('instances', help='instances.jsonl from build_benchmark')
    parser.add_argument('out')
    parser.add_argument('--per-stratum', type=int, default=34)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args(argv)

    strata = {}
    with open(args.instances, encoding='utf-8') as f:
        for line in f:
            instance = json.loads(line)
            strata.setdefault(stratum_of(instance), []).append(line)

    rng = random.Random(args.seed)
    with open(args.out, 'w', encoding='utf-8') as f:
        for name in sorted(strata):
            pool = strata[name]
            picked = pool if len(pool) <= args.per_stratum else rng.sample(pool, args.per_stratum)
            print(f'{name}: {len(picked)}/{len(pool)}')
            for line in picked:
                f.write(line)


if __name__ == '__main__':
    main()
