# Pilot: LLM as platform adjudicator (40 stratified cases)

Setup: 40 cases sampled from the 35,187-instance benchmark, 10 per rulebook
generation (`python -m benchmark.sample instances.jsonl pilot.jsonl
--per-stratum 10 --seed 7`). The adjudicator (Claude Fable 5, in-session,
blind to `official_text`) saw only the reported post, poster profile and
reporter statements, and output verdict / cited article / penalties.
Scored with `python -m benchmark.score`.

## Results

| metric | score |
|---|---|
| verdict agreement | **97.5%** (39/40) |
| cited article exact match | 60.0% |
| penalty-type set Jaccard | 53.3% |
| credit points exact | 42.5% |
| credit points MAE (when both sides deducted) | 1.12 |

## Error analysis — the disagreements are the findings

**1. The platform often rules "false" without sanctioning (the whole `other`
stratum).** 9/10 cases in the fourth stratum are informal verdicts: the
platform declares the post false and cites the debunker, but issues no
penalty and cites no article — mostly naive reshares of disaster-relief
hoaxes (鲁甸地震寻人 series). The LLM, told to adjudicate, imposed the
standard 2-point deduction. The platform appears to distinguish malicious
originators from good-faith spreaders; nothing in the case materials signals
that distinction.

**2. Sanction severity is era-driven, not (only) content-driven.** In
2012–2013 the platform gave 5 points + 7-day mute for a food-safety myth
(地沟油/大蒜) and a celebrity-death rumor, but only 2 points for a fabricated
sex-scandal smear of officials. The LLM's content-based severity reasoning
(harsher for political smears, milder for recycled folk myths) repeatedly
inverted the platform's actual tariffs. Judging by the penalty×year tables
(docs/concentration.md), the platform's overall severity dropped sharply
after 2013 — agreement on magnitude requires knowing *when* the case was
judged, not just what it says.

**3. Article citation varies within an era.** Cases from 2015 cite 第19条,
第22条 and 第23条 under different rulebook versions; an era→article heuristic
tops out around 60%. This is the cleanest motivation for the policy-as-prompt
condition (`run_eval --rules`): give the model the actual rulebook text in
force at case time and re-measure.

**4. Base rate vs. epistemic caution.** The one verdict miss was a case with
no reporter statement and an unverifiable claim, where the adjudicator chose
`undetermined`; the platform upheld. Since only substantiated cases are
publicized (97.9% upheld), a calibrated adjudicator should almost never
abstain — but that calibration comes from the archive's selection bias, not
from case evidence.

## Caveats

- Single adjudicator run, in-session (not via the API harness); n=40.
- The adjudicator knew aggregate platform practice (tariff structure, era
  rulebooks) — comparable to a policy-primed condition, not a zero-knowledge one.
- Several sampled rumors are historically well-known; memorization of the
  underlying facts (not of the verdicts) likely helps verdict accuracy.

## Next steps

1. Run the same 136-case stratified sample (`--per-stratum 34`) through
   `benchmark/run_eval.py` with an API key, three conditions: zero-shot /
   era-hinted / policy-as-prompt (rulebook text via `--rules`).
2. Add a "no-penalty" option to the schema so the model can reproduce the
   informal-verdict class (finding 1).
3. Report per-stratum agreement; use `credit_MAE` and severity direction
   (harsher/milder than platform) as the headline fairness metrics.
