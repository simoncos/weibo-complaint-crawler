# Revision and release protocol

The project may advance from internal exploration to a submission candidate
only when every gate below has evidence attached to a specific commit.

## Gate 1 — Data governance

- synthetic-only public fixtures;
- full dump and derived JSONL kept under controlled access;
- ethics/terms/data-processing determination documented;
- automated scan plus manual privacy audit passed;
- Git-history remediation decision recorded.

## Gate 2 — Provenance

- dump SHA-256, bytes, record count, schema and collection scope recorded;
- generated reports linked to dump hash and code commit;
- Python/dependency/model versions frozen;
- no manual copy step without hash comparison.

## Gate 3 — Measurement validity

- stable UID coverage and nickname fallback rate reported;
- 20-reporter truncation and complete-case sensitivity reported;
- timestamp and statement missingness reported for every derived metric;
- official parser and reporter types validated by two annotators plus
  adjudication;
- URL presence is not described as evidence quality without separate coding.

## Gate 4 — Benchmark validity

- input, gold and linkage physically separated;
- one fixed sample selected from observed time rather than gold labels;
- zero-shot, era-hint and policy-prompt conditions frozen and paired;
- policy text/date/hash verified per case;
- majority baseline, class support, uncertainty, failures and repeated runs
  reported;
- raw pilot accuracy not presented as a formal result.

## Gate 5 — Claim language

- public-archive selection distinguished from all submitted reports;
- visible reporter profiles distinguished from all reporters;
- descriptive association distinguished from state entry, intent or causal
  policy effects;
- every headline number reproducible from the release package.

Current status: Gates 1-4 have implementation scaffolding, but none has passed
on the full controlled dataset. The project remains **internal / major
revision**.
