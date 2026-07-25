# weibo-complaint-crawler

Historical crawler and research toolkit for public Weibo Community Management
Center complaint decisions collected through 2018.

> **Research status:** internal revision work in progress. The full dump and
> derived benchmark contain personal data and are **not approved for public
> release**. The tracked JSONL fixture is synthetic. Read
> [docs/data_governance.md](docs/data_governance.md) before using any data.

## Repository layers

- Legacy crawler (`weibo.py`, `extract.py`, `driver.py`, `mongo.py`): the
  original Selenium/MongoDB collection code. It has not been modernized for
  current Weibo pages or current Selenium APIs.
- Analysis (`analysis/`): dump loading, adjudication parsing, descriptive
  statistics, concentration analysis and reporter profiles.
- Benchmark (`benchmark/`): construction, sampling, model evaluation and
  scoring for the exploratory LLM-as-adjudicator study.
- Research documentation (`docs/`): current findings, limitations, handoff and
  revision protocol.

## Data boundary

The original dump was previously reported to contain 36,075 public complaint
records collected between 2012 and 2018; that count has not been reproduced in
this checkout. The dump is intentionally absent from Git. Before any analysis
run, create a local manifest with its SHA-256, byte size, record count, source
and schema version. Do not upload raw or merely pseudonymized text to a
third-party API without an approved data-processing decision.

The repository includes one fully synthetic fixture:

```bash
python -m tests.test_analysis
python -m analysis.stats data/sample_complaints.jsonl
```

## Current research claims

The reports in `docs/` are exploratory outputs from an off-repository dump.
They are not independently reproducible from the current checkout and should
not be cited as validated results until the revision gates in
`docs/revision_protocol.md` are complete.

The consolidated review findings, their disposition, and the ordered remaining
work are tracked in `docs/review_and_todos.md`.

Two directions remain under development:

1. Describing reporters visible in the public complaint archive. This must be
   limited to the visible-report estimand and audited for the 20-reporter page
   cap, missing timestamps and identity resolution.
2. Comparing LLM adjudications with historical platform outcomes. The 40-case
   pilot is exploratory; a frozen, paired, preregistered API experiment has not
   yet been run.

## Safety checks

Before committing any data-like artifact:

```bash
python scripts/scan_sensitive_artifacts.py
python -m tests.test_analysis
```

The scanner is a release guard, not proof of anonymization. Human privacy and
ethics review remains mandatory.

## Historical data source

The source was the Weibo Community Management Center at
`service.account.weibo.com`. The original Baidu share and collected dump are
not treated as publication authorization. Redistribution, platform terms,
research ethics and data-subject risk require a separate documented review.
