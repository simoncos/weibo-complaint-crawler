"""Sample benchmark inputs by independently observed post-time era.

Sampling never reads official adjudication text or gold labels. The same frozen
sample is reused for all experimental conditions.
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


STUDY_ERAS = {'era_2012_2013', 'era_2014_2016', 'era_2017_2018'}
VALID_ERAS = STUDY_ERAS | {'unknown', 'outside_study_window'}


def stratum_of(instance):
    era = instance.get('era', 'unknown')
    return era if era in VALID_ERAS else 'unknown'


def sample_records(records, per_stratum=34, seed=42, include_nonstudy=False):
    strata = defaultdict(list)
    seen_ids = set()
    for record in records:
        case_id = record.get('case_id')
        if not case_id or case_id in seen_ids:
            raise ValueError(f'duplicate or missing input case_id: {case_id!r}')
        seen_ids.add(case_id)
        stratum = stratum_of(record)
        if include_nonstudy or stratum in STUDY_ERAS:
            strata[stratum].append(record)
    rng = random.Random(seed)
    selected = []
    counts = {}
    for name in sorted(strata):
        pool = strata[name]
        picked = pool if len(pool) <= per_stratum else rng.sample(pool, per_stratum)
        counts[name] = (len(picked), len(pool))
        for record in picked:
            selected.append({**record, 'sampling_stratum': name})
    selected.sort(key=lambda record: record['case_id'])
    return selected, counts


def filter_gold(gold_records, selected_ids):
    by_id = {}
    for record in gold_records:
        case_id = record.get('case_id')
        if not case_id or case_id in by_id:
            raise ValueError(f'duplicate or missing gold case_id: {case_id!r}')
        by_id[case_id] = record
    missing = sorted(selected_ids - set(by_id))
    if missing:
        raise ValueError(f'gold missing selected case_id: {missing[0]}')
    return [by_id[case_id] for case_id in sorted(selected_ids)]


def _read_jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path, records):
    with open(path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', help='model-facing inputs JSONL')
    parser.add_argument('out', help='frozen sampled inputs JSONL')
    parser.add_argument('--per-stratum', type=int, default=34)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--include-nonstudy', action='store_true')
    parser.add_argument('--gold', help='sealed gold JSONL')
    parser.add_argument('--gold-out', help='filtered sealed gold JSONL')
    parser.add_argument('--require-full', action='store_true',
                        help='fail unless every study era reaches per-stratum n')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    if bool(args.gold) != bool(args.gold_out):
        parser.error('--gold and --gold-out must be supplied together')
    if args.per_stratum <= 0:
        parser.error('--per-stratum must be positive')

    source_paths = {Path(args.inputs).resolve()}
    if args.gold:
        source_paths.add(Path(args.gold).resolve())
    output_paths = {Path(args.out).resolve()}
    if args.gold_out:
        output_paths.add(Path(args.gold_out).resolve())
    if len(output_paths) != 1 + bool(args.gold_out):
        parser.error('sample and sampled-gold outputs must be different files')
    if source_paths & output_paths:
        parser.error('an output path must not overwrite an input file')
    existing = [path for path in output_paths if path.exists()]
    if existing and not args.overwrite:
        parser.error(
            f'output already exists (use --overwrite intentionally): {existing[0]}')

    selected, counts = sample_records(
        _read_jsonl(args.inputs), args.per_stratum, args.seed,
        args.include_nonstudy)
    if args.require_full:
        underfilled = {
            era: counts.get(era, (0, 0))
            for era in STUDY_ERAS
            if counts.get(era, (0, 0))[0] < args.per_stratum
        }
        if underfilled:
            raise ValueError(f'underfilled preregistered strata: {underfilled}')
    _write_jsonl(args.out, selected)
    for name, (picked, available) in counts.items():
        print(f'{name}: {picked}/{available}')
    if args.gold:
        selected_ids = {record['case_id'] for record in selected}
        _write_jsonl(
            args.gold_out, filter_gold(_read_jsonl(args.gold), selected_ids))


if __name__ == '__main__':
    main()
