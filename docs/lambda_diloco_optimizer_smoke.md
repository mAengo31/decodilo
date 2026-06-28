# Lambda DiLoCo Optimizer Smoke

`dev diloco-optimizer-smoke` is a local/offline bounded optimizer-fidelity smoke
command intended as the next safe synthetic step after the DiLoCo-shaped
protocol smoke baseline.

```bash
python -m decodilo.cli dev diloco-optimizer-smoke \
  --synthetic \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-diloco-optimizer-smoke.json
```

The command uses deterministic synthetic vector data only. It performs no
network access, package installation, data/model download, real model training,
torch work, GPU work, background service startup, or remote operation.

The smoke validates a tiny reference flow:

- one decoupled AdamW inner step over a fixed parameter vector and fixed
  synthetic gradient;
- pseudo-gradient construction as
  `initial_parameters - post_inner_parameters`;
- one Nesterov outer update using fixed momentum and learning rate;
- JSON-compatible optimizer state roundtrip; and
- strict deterministic reference-value comparison.

The report may state `optimization_fidelity=optimizer_semantics_smoke` when the
AdamW, pseudo-gradient, Nesterov, state roundtrip, and reference-value checks all
pass. It must not claim full DiLoCo training, model training, or parameter
fragment semantics. The current command reports
`parameter_fragment_semantics=not_exercised`.

All reports must keep `launch_ready=false`, `launch_allowed=false`, and unsafe
activity flags set to false.
