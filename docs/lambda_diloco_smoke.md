# Lambda DiLoCo Smoke

`dev diloco-smoke` is a local/offline bounded DiLoCo-shaped synthetic smoke
command intended as the next safe remote experiment step after the learner/syncer
smoke baseline.

```bash
python -m decodilo.cli dev diloco-smoke \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --max-steps 1 \
  --out /tmp/decodilo-diloco-smoke.json
```

The command uses synthetic in-memory vectors, one learner, one sync/update
round, event-log replay, update-stream acknowledgement, and token-weighted
merge. It performs no network access, package installation, data/model download,
real training, torch work, GPU work, background service startup, or remote
operation.

The report is explicit about optimizer fidelity. The current path is
`diloco_shaped_protocol_only`: it exercises DiLoCo-shaped learner/syncer protocol
mechanics but does not claim full DiLoCo optimizer fidelity because the active
path does not run true inner AdamW plus outer Nesterov semantics.

All reports must keep `launch_ready=false`, `launch_allowed=false`, and unsafe
activity flags set to false.
