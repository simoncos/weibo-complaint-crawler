# MoA review and remaining TODOs

*Updated 2026-07-25. Branch: `claude/dataset-literature-review-khplj5`.*

## Current decision

The repository is suitable for continued **internal research development**, but
it is not a publication-ready dataset, completed empirical study, or validated
LLM benchmark.

Three independent review lenses were applied:

- methods and measurement validity;
- privacy, ethics, and reproducibility;
- benchmark design and software engineering.

Their pre-revision decisions were, respectively, **major revision**, **reject
public release**, and **reject formal performance claims**. The current changes
address the engineering and documentation defects that can be resolved without
the controlled full dump or external approvals. They do not close the empirical
or governance gates.

## Review findings and disposition

| Finding | Revision now present | Status |
|---|---|---|
| The public page exposes at most 20 reporter profiles, so visible rows were incorrectly treated as all reporters. | Analysis now states the visible-page estimand, reports completeness/truncation, a lower bound on hidden rows, and a confirmed-complete sensitivity subset. | Tooling complete; full-dump result pending. |
| Nicknames were treated as stable identities. | Numeric platform UID is preferred, identities are deduplicated within case, and nickname fallback is counted explicitly. | Tooling complete; UID coverage pending. |
| Missing timestamps/statements and heuristic account types were not validated. | Outputs expose effective sample sizes and missingness; a two-annotator plus adjudication workflow reports agreement, Cohen's kappa, and machine confusion. | Workflow complete; human annotations pending. |
| URL presence was described as evidence quality. | The metric is renamed URL presence among non-missing statements; evidence-quality claims are withdrawn. | Resolved at claim level. |
| Penalty tables mixed event counts and case denominators; an even-sample median was wrong. | Penalties are deduplicated per type per case, case-year denominators are explicit, and the conventional median is used. | Code fixed; full-dump rerun pending. |
| Real account data was present in tracked samples and reports; simple hashes were not anonymous. | The public fixture is synthetic, stale reports were removed, obvious-identifier scanning and a restricted-data policy were added. | Current tree guarded; Git-history risk remains. |
| The historical dump lacked a content manifest and reproducible provenance. | A manifest generator records SHA-256, bytes, record count, schema, code commit, and dirty state. | Generator complete; real dump not located. |
| The 40-case pilot had no frozen sample, baseline, independent runs, or auditable predictions. | The pilot is marked superseded and a paired three-condition protocol replaces it. | Protocol/tooling complete; formal run pending. |
| Model inputs, gold labels, and identifiable linkage could leak into one another. | Inputs, sealed gold, and restricted linkage are separate; the runner rejects gold/source/profile keys. | Resolved and regression-tested. |
| Failed/refused model calls could disappear from the denominator, and nested runner output scored incorrectly. | Strict schema validation accepts the runner wrapper, persists failures, and reports all-frozen-case exact rates plus conditional successful-response metrics. | Resolved and regression-tested. |
| Policy snapshots and effective dates were weakly verified. | Retrieval uses calendar distance, HTTP/content/article checks, hashes, human-verification flags, and non-overlapping effective intervals. | Fail-closed tooling complete; source verification pending. |
| A Boolean API flag was not an auditable privacy approval. | API execution requires an approval record bound to approval ID, purpose, provider, model, expiry, and frozen input SHA-256. | Gate implemented; real approval absent. |
| F2-F7 language exceeded the available evidence. | Old concentration, mechanism, sanction-change, evidence-quality, intent, and LLM-performance claims are withdrawn or explicitly provisional. | Resolved at documentation level. |

## TODOs

### P0 — required before any public release or external model run

- [ ] Recover `HK_DEV.WEIBO_COMPLAINT.json` from controlled storage.
- [ ] Generate the real data manifest and verify hash, size, record count,
  schema, collection scope, code commit, and a clean worktree.
- [ ] Complete the ethics, platform-terms, copyright, retention, data-subject,
  and third-party processing determination.
- [ ] Decide how to remediate historical Git commits, forks, and caches that may
  still contain real identifiers. Any history rewrite requires separate
  coordination and explicit force-push approval.
- [ ] Create the stratified human validation set; complete two independent
  annotations and adjudication; report class support, agreement, Cohen's kappa,
  parser accuracy, and reporter-type confusion.
- [ ] Retrieve and independently verify every historical policy version, exact
  effective interval, source URL, and file hash.
- [ ] Freeze Python and API SDK dependencies in a reproducible environment.
- [ ] Obtain a data-processing approval record bound to the exact sampled input
  hash and frozen model ID.

### P1 — required before empirical or benchmark claims

- [ ] Rerun descriptive analyses on the manifested dump and preserve
  hash-linked outputs inside the restricted environment.
- [ ] Report UID resolution/fallback coverage, page truncation, timestamp and
  statement missingness, and complete-case sensitivity before interpreting
  reporter concentration.
- [ ] Perform and document a power analysis; replace the inherited 34-per-era
  target if the design requires it.
- [ ] Freeze one observed-era sample and reuse it across zero-shot, era-hint,
  and policy-prompt conditions.
- [ ] Run at least three independently identified runs per condition without
  loading sealed gold.
- [ ] Report majority baseline, class support, all-case failure-adjusted exact
  rates, successful-response conditional metrics, uncertainty, per-era
  estimates, refusals/errors, and paired condition differences.
- [ ] Conduct restricted error analysis without copying identifiable examples
  into the public repository.

### P2 — publication positioning and optional follow-up

- [ ] Refresh the literature review with a documented primary-source search and
  verify novelty rather than claiming uniqueness.
- [ ] Define the public artifact: code-only, synthetic demonstration, aggregate
  report, or a separately reviewed de-identified release.
- [ ] If new crawling is considered, treat it as a separate compliance and
  engineering project; the legacy Selenium crawler is not evidence that current
  collection is permitted or operational.
- [ ] Treat co-occurrence networks as descriptive unless an additional design
  can distinguish coordination, intent, or causal effects.

## Verification contract

Before the next commit or study run:

```bash
python3 -m pytest -q
python3 -m compileall -q analysis benchmark scripts tests
python3 scripts/scan_sensitive_artifacts.py
git diff --check
```

The current synthetic checks establish only that the revised tooling contracts
work on controlled fixtures. They do not validate historical findings.

## Related documents

- `data_governance.md` — privacy and release boundary.
- `validation_protocol.md` — human gold workflow.
- `benchmark_protocol.md` — formal paired experiment.
- `revision_protocol.md` — publication gates.
- `research_notes.md` — current F1-F7 claim boundary.
- `HANDOFF.md` — local continuation commands and blockers.
