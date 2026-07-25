# Full-dump report — stale artifact removed

The previous generated report contained unreproduced counts and identifiable
account names. It has been removed from the current tree.

Regenerate it only inside the restricted data environment after recording the
dump manifest and completing the validation protocol:

```bash
python -m analysis.stats "$DUMP" --markdown /restricted/full_dump_report.md
```

Do not copy a generated report into the public repository until its free text,
account labels, denominators and release status have been reviewed.
