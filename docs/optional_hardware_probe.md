# Optional Hardware Probe

The hardware probe is informational and local-only.

```bash
python -m decodilo.cli hardware probe
```

It reports CPU availability, whether optional torch is importable, and CUDA/MPS
availability if torch is installed. It does not read credentials, contact the
network, launch cloud resources, initialize distributed torch, or require GPUs.

Optional single-device timing is explicit:

```bash
python -m decodilo.cli perf single-device \
  --device cpu \
  --trainer torch_causal_lm \
  --steps 20 \
  --out /tmp/decodilo-single-device.json
```

CUDA or MPS requires `--allow-accelerator` and availability. Default tests do
not run accelerator paths.

