# Reporter profiles — restricted regeneration required

The old checked-in profiles exposed real account names and reported medians
without effective sample sizes. They have been removed from the current tree.

The revised command keys profiles by numeric UID when available and reports
known/missing timestamps plus latency effective n:

```bash
python -m analysis.reporter_profiles "$DUMP" --top 10 \
  --out /restricted/reporter_profiles.md
```

Generated profiles contain real text and must remain inside the restricted
environment unless a separate release review approves them.
