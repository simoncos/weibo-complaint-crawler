# Data governance and release gate

## Current classification

The original complaint dump and all benchmark instances derived from it are
**restricted research data**. They are not anonymous and are not approved for
public release.

Public visibility at collection time does not by itself establish permission
to redistribute, send to third-party APIs, or preserve indefinitely. Before
publication, the project needs a documented ethics determination and a review
of applicable platform terms, copyright, data-protection and institutional
requirements.

## Prohibited repository content

Do not commit:

- raw or derived complaint JSON/JSONL/NDJSON;
- account names, stable platform IDs, profile or avatar URLs;
- contact details, exact locations or exact timestamps linked to a person;
- verbatim complaint, rumor or adjudication text from real cases;
- API prompts or responses containing any of the above;
- a reversible nickname hash presented as anonymous data.

`data/sample_complaints.jsonl` is the sole exception because it is synthetic.

## Required release gates

1. Record the source dump hash, schema, collection scope and access boundary
   with `scripts/build_data_manifest.py`. The placeholder in
   `docs/data_manifest.example.json` is not evidence that the dump was found.
2. Replace platform identifiers with random release-local IDs. Store any
   linkage map outside the release package under access control.
3. Remove URLs, handles and contact details; coarsen time and geography.
4. Scan free text for named entities and quasi-identifiers, then manually audit
   a stratified sample, including minors and sensitive allegations.
5. Separate model inputs from sealed gold labels and identifiable error-analysis
   text.
6. Document whether third-party API processing is allowed and what text leaves
   the controlled environment. Bind the approval record to the SHA-256 of the
   exact frozen model-input file and the allowed provider/model.
7. Provide a data-subject contact/deletion process and a versioned release log.

Passing `scripts/scan_sensitive_artifacts.py` is necessary but insufficient.

## Local manifest command

```bash
python scripts/build_data_manifest.py /restricted/path/HK_DEV.WEIBO_COMPLAINT.json \
  --out /restricted/path/data_manifest.json
```

Keep the manifest beside the controlled dataset until its filename and
metadata have been reviewed for publication. A publishable copy may contain
the content hash and record count, but never the absolute local path.

## Git history

Earlier public commits contain a real sample in README and JSONL form. Removing
it from the current tree does not remove it from Git history, forks or caches.
History remediation is a separate destructive operation and requires an
explicit decision covering coordination, force-push consequences and mirrors.
