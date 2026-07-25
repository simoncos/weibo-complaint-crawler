# Historical policy retrieval and verification

Policy-as-prompt evaluation is blocked until every policy text and exact
effective interval is human verified.

## Retrieval

```bash
python scripts/fetch_rules.py --out data/rules
```

The script now:

- calculates snapshot distance with calendar dates;
- searches a bounded three-year CDX window;
- fails on HTTP/retrieval errors;
- checks minimum text size and the expected main article;
- records snapshot provenance and text SHA-256;
- exits non-zero if any target fails.

Automated retrieval does not establish the effective dates. The same
`/roles/guiding` URL changed content, and a nearby snapshot can postdate a
policy transition.

## Human verification

For each retrieved text:

1. compare the title and revision date with independent primary-source
   evidence;
2. verify the definition, main false-information article and sanction table;
3. record exact non-overlapping `effective_from`/`effective_to` dates;
4. confirm the file hash matches its `.meta.json`;
5. change `human_version_verified` only after a second reviewer checks it.

Expected article checks inherited from archived adjudications are:

- first-generation trial rules: Article 22;
- second-generation trial rules: Article 22;
- second-generation final rules: Article 23;
- third-generation complaint rules: Article 19.

These checks can reject a wrong snapshot but cannot prove the snapshot is the
correct version.

## Benchmark manifest

Copy `docs/rules_manifest.example.json` to the restricted execution directory
and replace every `PENDING_*` field with reviewed dates, source URLs and hashes.
`benchmark.run_eval --condition policy_prompt` intentionally refuses to run
with pending, missing, overlapping or hash-mismatched policy periods.
