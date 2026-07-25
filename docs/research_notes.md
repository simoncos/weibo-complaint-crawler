# Research status after methodological review

*Updated 2026-07-21. This replaces the earlier F1-F7 summary as the current
interpretation boundary.*

## Evidence status

The off-repository dump was previously reported to contain 36,075 public
complaint decisions from 2012-2018. The dump is not available in the current
workspace, has no recorded SHA-256 manifest, and has not been rerun through the
revised analysis. Consequently the historical numeric reports are exploratory
artifacts, not independently reproduced results.

## Claim-by-claim disposition

### F1 — Archive selection: retained with narrow wording

The archived output reported that almost all publicized cases were upheld. The
valid claim is only that the **public decision archive** is highly selected. It
does not estimate all submitted reports, rejected reports that were not
publicized, or rumor prevalence. The exact percentage must be regenerated and
human-validated before citation.

### F2 — Reporter concentration: provisional, requires rerun

The old Gini, Top-K and unique-reporter numbers used visible profiles and
grouped identities by nickname. The revised code:

- uses numeric profile UID where available;
- deduplicates an identity within a case;
- explicitly estimates visible public-page appearances;
- reports the 20-reporter truncation lower bound;
- provides a confirmed-complete-case sensitivity subset.

Until the controlled dump is rerun, do not cite the old concentration numbers
or describe them as the full reporter population.

### F3 — Government participation: hypothesis, not established mechanism

Keyword-based account classification and sparse timestamps do not support the
previous mechanism language about state entry or retrospective enforcement.
The revised output reports effective timestamp counts and marks account type as
heuristic. A stratified human validation set, missingness analysis and
alternative explanations are required before making temporal comparisons.

### F4 — Sanction change: old percentage withdrawn

The previous penalty table summed multiple penalty events within a case while
labeling the row total as cases, and assigned year using a report-time proxy.
The revised analysis counts each penalty type once per case, uses all cases in
the case-year proxy as denominator, and labels the time variable honestly.
The old 23%-to-5% mute claim is withdrawn pending regeneration.

### F5 — Evidence quality: withdrawn and renamed

An `http(s)` marker measures URL presence, not evidence quality. The revised
analysis separates missing statements from present statements and reports URL
presence only, including a complete-case sensitivity table. Any evidence-
quality claim requires an annotation guide, two annotators, validity metrics
and adjustment for changing reporter composition.

### F6 — Informal no-penalty outcomes: exploratory coding hypothesis

The parser retains an `upheld_informal` category, but neither its precision nor
the interpretation of good-faith resharing has been validated. Do not state
that the platform inferred intent without manual review and supporting case
materials.

### F7 — LLM adjudication: pilot only, not a result

The previous 40-case in-session exercise lacked a frozen sample, predictions,
baseline, independent runs and an auditable prompt. Its 97.5% verdict agreement
must not be used as evidence that an LLM reproduces platform adjudication.
`docs/benchmark_protocol.md` defines the replacement paired experiment.

## Current research directions

Direction B remains viable as a descriptive study of **reporter profiles
visible in publicized complaint cases**, provided the full data manifest,
identity resolution, truncation sensitivity and human validation gates pass.

Direction A remains viable as an exploratory benchmark of historical outcome
agreement, with penalty and article agreement as primary substantive targets.
It cannot make claims about de-novo fact checking, intent, legitimacy or causal
policy effects without additional design work.

## Reproduction gates

- [x] Synthetic public fixture and automated sensitive-artifact scan.
- [x] Dump-manifest generator.
- [x] UID-based visible-reporter analysis and complete-case sensitivity output.
- [x] Two-annotator plus adjudication validation tooling.
- [x] Strict scorer and end-to-end format tests.
- [x] Input/gold separation and draft three-condition benchmark protocol.
- [ ] Locate the controlled dump and record its real hash.
- [ ] Complete human annotations and report validation metrics.
- [ ] Retrieve and human-verify policy versions and effective dates.
- [ ] Freeze the API dependency environment and approve data processing.
- [ ] Run the full analysis and formal benchmark.

See `docs/revision_protocol.md` for the release decision rules.
