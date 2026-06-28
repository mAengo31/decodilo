# Tiny Real Training Smoke

`dev tiny-real-training-smoke` is a local/offline CPU-only command for the
post-scaffold scientific branch. It verifies tiny real training mechanics over
deterministic synthetic in-memory data:

```bash
python -m decodilo.cli dev tiny-real-training-smoke \
  --synthetic \
  --model tiny-linear \
  --steps 1 \
  --optimizer adamw \
  --out /tmp/decodilo-tiny-real-training-smoke.json
```

The command creates a tiny linear model locally, runs a forward pass, computes
MSE loss, computes analytic gradients, checks those gradients against a finite
difference reference, applies one AdamW update, verifies optimizer state, and
checks deterministic replay.

It performs no network access, package installation, dataset download, model
download, GPU work, long-running training, or background process. It uses
pure-Python arithmetic, so `torch_required=false`.

The report may claim tiny real training mechanics only. It must not claim real
model-scale training, dataset pipeline validation, distributed DiLoCo training,
or paper-scale DiLoCo.
