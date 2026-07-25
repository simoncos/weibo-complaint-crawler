# Local continuation handoff

*Updated 2026-07-25 after independent methods, privacy and benchmark review.*

## Current state

The project is an internal research revision, not a publication-ready dataset
or benchmark. The old crawler remains historical. The revised analysis and
benchmark tooling run on the synthetic fixture, but the full dump, human gold
set, verified rule texts and formal API results are absent.

See `review_and_todos.md` for the consolidated MoA findings, revision
disposition, and P0-P2 completion queue.

## What is implemented

- synthetic public fixture and restricted-data release gate;
- automated scan for obvious identifiers in data-like artifacts;
- dump SHA-256/record-count manifest generator;
- UID-based visible-reporter concentration analysis;
- truncation, timestamp and statement-missingness reporting;
- correct per-case penalty denominators and conventional medians;
- two-annotator/adjudication validation-set workflow;
- separated model inputs, sealed gold and optional restricted linkage;
- post-time-era sampling independent of adjudication labels;
- isolated zero-shot, era-hint and verified policy-prompt conditions;
- strict scoring, failure denominators, majority baseline and uncertainty output;
- hardened rule retrieval with true calendar distance, hashes and fail-closed
  validation.

## Immediate commands

```bash
python scripts/scan_sensitive_artifacts.py
python -m tests.test_analysis
python -m analysis.stats data/sample_complaints.jsonl
python -m analysis.concentration data/sample_complaints.jsonl
```

## External/manual blockers

1. Recover `HK_DEV.WEIBO_COMPLAINT.json` from controlled storage and run:

   ```bash
   python scripts/build_data_manifest.py "$DUMP" \
     --out /restricted/data_manifest.json
   ```

2. Generate and complete the human validation set described in
   `docs/validation_protocol.md`.
3. Retrieve historical policies, manually verify exact effective dates and
   complete a rules manifest. The checked-in example intentionally fails.
4. Obtain a documented ethics/data-processing decision before sending any case
   text to an external API.
5. Freeze Python and Anthropic SDK versions for the execution environment.
6. Run `docs/benchmark_protocol.md`; do not reuse the historical pilot numbers.

## Historical Git risk

The current tree replaces the real sample with synthetic data, but earlier Git
history and public mirrors may still contain the original identifiers. History
rewriting is intentionally not performed here because it requires explicit
coordination and force-push approval.
