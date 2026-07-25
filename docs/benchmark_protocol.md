# Preregistered benchmark protocol (draft; not yet executed)

This document defines the experiment that must replace the exploratory 40-case
pilot. It is a protocol draft, not a claim that a formal evaluation exists.

## Research question

Can a language model reproduce historical platform outcomes beyond the archive
base rate, and does contemporaneous policy context improve article and sanction
agreement?

## Frozen data flow

1. Generate a versioned dump manifest and complete the privacy/API processing
   gate.
2. Build physically separated model inputs, sealed gold and restricted linkage:

   ```bash
   python -m benchmark.build_benchmark "$DUMP" /restricted/inputs.jsonl \
     --gold-out /restricted/gold.jsonl \
     --linkage-out /restricted/linkage.jsonl
   ```

3. Sample 34 cases from each independently observed post-time era
   (`2012-2013`, `2014-2016`, `2017-2018`), seed 42. Unknown/out-of-window cases
   are excluded by default. The same 102 case IDs are used for every condition.

   ```bash
   python -m benchmark.sample /restricted/inputs.jsonl /restricted/sample.jsonl \
     --per-stratum 34 --seed 42 \
     --require-full \
     --gold /restricted/gold.jsonl \
     --gold-out /restricted/sample_gold.jsonl
   ```

The final sample size must be revisited with a power analysis before execution;
102 is retained only as the inherited pilot expansion target.

## Paired conditions

- `zero_shot`: case materials and output schema only. No policy generation,
  historical tariff, base-rate or no-penalty hint.
- `era_hint`: the same case plus its preregistered study era.
- `policy_prompt`: the same case plus the exact human-verified policy text in
  effect on `policy_date`, selected from a non-overlapping interval manifest.

The model, SDK, prompt hashes, rule hashes, temperature, token limit and run ID
are recorded per case. Run order should be randomized outside the model, and at
least three independent runs per condition are required to quantify stochastic
variation. A run must never load sealed gold.

## API gate and execution

No API call is permitted without a machine-checked data-processing approval
record. It binds an approval ID, purpose, provider, allowed model, expiration
date and the frozen model-input file SHA-256. Copy
`data_processing_approval.example.json` outside the repository, complete it
through the applicable review process, and pass its path below. The example
rules manifest also intentionally fails until dates, texts and hashes are human
verified.

```bash
python -m benchmark.run_eval /restricted/sample.jsonl \
  --condition zero_shot --model "$MODEL_ID" --run-id zero-01 \
  --out /restricted/zero-01.jsonl \
  --data-processing-approval /restricted/data_processing_approval.json

python -m benchmark.run_eval /restricted/sample.jsonl \
  --condition era_hint --model "$MODEL_ID" --run-id era-01 \
  --out /restricted/era-01.jsonl \
  --data-processing-approval /restricted/data_processing_approval.json

python -m benchmark.run_eval /restricted/sample.jsonl \
  --condition policy_prompt --model "$MODEL_ID" --run-id policy-01 \
  --rules-manifest /restricted/rules_manifest.json \
  --out /restricted/policy-01.jsonl \
  --data-processing-approval /restricted/data_processing_approval.json
```

Use `--dry-run` first. Each planned case produces one success, refusal, error or
dry-run record; failures remain in the denominator and outputs are never
silently overwritten.

## Preregistered outcomes

Primary outcomes:

- exact full-penalty agreement over every frozen case, with refusals and errors
  scored as non-matches;
- credit-point MAE, conditional on both sides deducting credit;
- direction of sanction difference, after a severity ordering is frozen.

Secondary outcomes:

- article exact match and Jaccard;
- penalty-type Jaccard;
- verdict macro F1 and balanced accuracy;
- per-era estimates and paired condition differences.

Always report the majority-verdict baseline, class support, confusion matrix,
Wilson interval for verdict agreement, refusals/errors and the number actually
scored. Successful-response-only metrics must be labeled conditional; the
failure-adjusted exact rates use every frozen case as denominator. Do not
headline raw verdict accuracy when the archive is overwhelmingly upheld.

## Contamination and interpretation

Historical rumors may occur in model training data. The study measures outcome
agreement on this archive, not de-novo fact-checking ability. Any causal claim
that policy text improves reasoning requires the paired design and must remain
separate from memorization or base-rate explanations.

## Pending gates

- full dump manifest and reproducible sample are absent;
- rules and exact effective dates are unverified;
- human gold-set validation is incomplete;
- data-processing approval and dependency lock are absent;
- no paid API run has been performed under this protocol.
