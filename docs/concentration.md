# Concentration report — regeneration required

The former report used nickname identity, treated visible reporter rows as the
full population and mislabeled summed penalty events as cases. Its numbers are
withdrawn.

The revised analysis emits observation coverage, UID resolution, the lower
bound of reporter-page truncation, a confirmed-complete-case sensitivity
subset, statement/time missingness and per-case penalty prevalence:

```bash
python -m analysis.concentration "$DUMP" --out-dir /restricted/concentration
```

No revised full-dump output exists because the controlled dump has not been
located in this workspace.
