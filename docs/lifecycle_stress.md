# Lifecycle Stress

Milestone 013 adds a local lifecycle stress runner for repeated checkpoint,
compaction, snapshot, recovery-manifest, replay, audit, and GC-plan cycles.
It is still a local-only harness: it does not launch cloud resources, call
provider APIs, require GPUs, or require remote artifact storage.

The stress runner starts a normal local run, then repeatedly:

- writes segmented event logs
- writes a replay snapshot
- compacts the idempotency store
- refreshes the recovery manifest chain
- creates a dry-run GC plan
- validates the run
- compares genesis replay with snapshot-plus-tail replay
- audits artifact references

Example:

```bash
python -m decodilo.cli lifecycle stress \
  --workdir /tmp/decodilo-m013-stress \
  --learners 2 \
  --steps 120 \
  --min-quorum 1 \
  --seed 123 \
  --compact-every-rounds 3 \
  --snapshot-every-compactions 2 \
  --gc-plan-every-compactions 2 \
  --out /tmp/decodilo-m013-stress/lifecycle_stress_report.json
```

The report contains cycle counts, replay results, artifact-audit status,
validation status, event segment counts, and GC reclaimable-byte estimates.
A pass means the local lifecycle artifacts are internally consistent. It does
not mean the system is ready for cloud launch.

