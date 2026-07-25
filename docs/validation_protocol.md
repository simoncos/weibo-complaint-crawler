# Human validation protocol

Coverage is not accuracy. Before citing parsed verdicts, account types or
evidence categories, create a stratified human gold set from the controlled
dump:

```bash
python -m analysis.validation sample "$DUMP" /restricted/validation.jsonl \
  --per-stratum 25 --seed 42
```

The output is restricted because it contains verbatim profile descriptions and
official adjudication text. It must not be committed.

## Annotation workflow

1. Two annotators independently fill `annotator_a` and `annotator_b` without
   seeing each other's labels.
2. A third pass resolves disagreements in `adjudicated_label` and records the
   reason in `notes`.
3. For `official_parser`, labels use this shape:

   ```json
   {
     "verdict": "upheld",
     "cited_articles": [19],
     "penalties": [{"type": "credit_deduction", "magnitude": 2}]
   }
   ```

4. For `reporter_type`, labels are one of `government`, `media`, `legal`,
   `debunker`, `ordinary`, or `uncertain`.
5. Report agreement and machine performance with:

   ```bash
   python -m analysis.validation score /restricted/validation.jsonl \
     --out /restricted/validation_report.md
   ```

## Publication gate

Do not call the parser or identity heuristic validated until:

- rare verdicts and every reporter type have adequate resolved sample sizes;
- annotator disagreement is reported;
- verdict/article/penalty accuracy and reporter-type confusion are reported;
- the sample seed, dump hash, code commit and annotation guide are frozen.

The current repository contains no completed human gold set, so this gate is
**pending**.
