# weibo-complaint-crawler

Legacy Python crawler for complaint pages that were historically exposed by the
Weibo Community Management Center.

## Status and evidence boundary

This `master` snapshot is crawler source code, not a verified dataset or a
completed research result. The repository does not contain the source-data
manifest, checksums, collection log, de-duplication audit, or missingness
analysis needed to reproduce or validate the historical dataset-size claim that
appeared in earlier versions of this README. It also lacks the rights review
needed for a responsible release. The claim and direct download instructions
have therefore been removed from the current README rather than presented as
verified facts.

No live website, account, real complaint record, Mongo deployment, or remote CI
was used to validate the changes in this worktree. The automated checks use only
synthetic URLs, fake browser objects, fake Mongo objects, and synthetic marker
text. Passing them is evidence for the local control flow only; it is not
evidence that the historical selectors still work or that collection is lawful,
complete, representative, or suitable for publication.

## Current control-flow guarantees

- URL discovery checkpoints the current page before looking for another page.
- Only a control explicitly labelled as the next page is followed; a repeated
  page signature stops pagination.
- Checkpoint URLs are stripped, empty lines are discarded, and duplicates are
  removed while preserving first-seen order. Each rewrite uses an atomic file
  replacement.
- When a worker reaches its exception threshold, it flushes successful buffered
  records and recycles only that worker's browser. It does not re-execute the
  program entry point.
- The complaint-detail worker writes parsed records to Mongo but does not print
  successful records to standard output. Its normal progress logs contain worker
  state and counts rather than full records.

These guarantees are covered by offline tests in `tests/test_weibo.py`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

## Data contract example

The following object is synthetic. It illustrates shape only and does not
represent a Weibo user, post, or complaint.

```json
{
  "url": "https://example.invalid/complaints/synthetic-001",
  "title": "Synthetic complaint title",
  "reports": [
    {
      "reporter_url": "https://example.invalid/users/reporter-001",
      "reporter_name": "synthetic-reporter",
      "report_time": "2000-01-01 00:00",
      "report_text": "Synthetic reporter statement."
    }
  ],
  "actual_reporter_count": 1,
  "rumor": {
    "rumorer_name": "synthetic-subject",
    "rumorer_url": "https://example.invalid/users/subject-001",
    "rumor_time": "2000-01-01 00:00:00",
    "rumor_url": "https://example.invalid/posts/synthetic-001",
    "rumor_text": "Synthetic reported text."
  },
  "official": {
    "official_text": "Synthetic outcome text."
  },
  "looks": []
}
```

## Privacy, rights, and research boundary

Complaint records may contain account identifiers, profile attributes,
locations, free text, and other personal data. URL checkpoints, Mongo records,
terminal captures, backups, and exported files must therefore be treated as
sensitive even though the original pages may have been publicly visible.

Before any live collection or use, the operator must independently establish a
lawful and ethical basis, review current platform terms and technical access
rules, minimize collected fields, restrict access, define retention and deletion
procedures, and provide an appropriate correction or takedown path. The crawler
must not be used to bypass access controls or anti-automation measures.

This repository currently contains neither a code license nor a data license.
No permission to reuse the code or redistribute historical data should be
inferred from this README. Removing the old download directions and identifiable
example from the current file does not remove them from Git history or revoke
copies that may already exist; any broader remediation requires a separate,
explicit rights and publication review.

Until provenance, consent or other legal basis, data minimization, retention,
re-identification risk, and human research review (where applicable) are
documented, outputs should remain access-controlled and must not be described as
a public dataset or validated empirical study.
