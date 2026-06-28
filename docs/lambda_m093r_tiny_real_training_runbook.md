# M093R Tiny Real Training Runbook Preview

M092 may authorize a future supervised M093R review only after the local
`dev tiny-real-training-smoke` command passes and the tiny-real-training policy
passes. The authorization remains future-only:

- `run_now=false`
- `launch_ready=false`
- `launch_allowed=false`
- `billable_action_performed=false`

The future remote command, if separately approved, is:

```bash
env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src \
  python3 -m decodilo.cli dev tiny-real-training-smoke \
  --synthetic \
  --model tiny-linear \
  --steps 1 \
  --optimizer adamw \
  --out /tmp/decodilo-tiny-real-training-smoke.json
```

M093R must still pass fresh source bundle validation, dependency bundle
validation, manifest validation, fresh read-only discovery, plan/gate,
one-shot arming, targeted tests, quick profile, Ruff, and secret/value scans.

The command validates tiny real training mechanics only. It does not authorize
dataset download, model download, internet package installation, benchmark,
stress test, paper-scale DiLoCo, distributed training, or real model-scale
training claims.
