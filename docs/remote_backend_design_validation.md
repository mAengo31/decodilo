# Remote Backend Design Validation

The design validation report compares a requirement set against simulator
evidence, capability gaps, security checks, lifecycle checks, and optional cost
estimates.

Design status values:

- `not_ready`: blockers exist.
- `simulation_only_passed`: local simulator evidence passed, but no real backend
  exists.
- `requires_real_backend_implementation`: reserved for future work after a real
  backend exists and is independently validated.

Blockers include insufficient read/write bandwidth, missing conditional put,
missing integrity metadata, missing security controls, lifecycle gaps, or
simulation errors.

```bash
python -m decodilo.cli remote validate-design \
  --requirements /tmp/decodilo-remote-requirements.json \
  --sim-report /tmp/decodilo-remote-sim.json \
  --out /tmp/decodilo-remote-design-validation.json
```

The report always keeps `remote_backend_enabled=false`, `launch_ready=false`,
and `launch_allowed=false`.

Milestone 016 adds a separate readiness gate. Even complete simulator and
conformance evidence can only reach `implementation_review_required`; it cannot
authorize SDK addition or enable a real backend.
