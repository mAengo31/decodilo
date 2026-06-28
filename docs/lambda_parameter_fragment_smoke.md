# Lambda Parameter-Fragment Smoke

`dev parameter-fragment-smoke` is a local/offline bounded synthetic smoke that
validates a tiny vector-fragment synchronization path.

```bash
python -m decodilo.cli dev parameter-fragment-smoke \
  --synthetic \
  --fragments 2 \
  --max-steps 1 \
  --out /tmp/decodilo-parameter-fragment-smoke.json
```

The command uses deterministic in-memory vector data only. It performs no
network access, package installation, data/model download, real training,
torch/GPU work, background service start, or remote command. It writes one
bounded JSON report.

The smoke splits `[1.0, 2.0, 3.0, 4.0]` into two synthetic fragments, applies
one deterministic update to `fragment_1`, increments that fragment version,
reconstructs the full vector, roundtrips fragment state through a JSON-safe
representation, and compares the result with a strict reference value.

The report may state
`parameter_fragment_semantics=synthetic_vector_fragments` because it exercises
vector/tensor-like fragments. It must not claim `true_model_fragment`,
communication/computation overlap, quantized communication, real model
training, or full Streaming DiLoCo.

The command is intended as the next bounded remote parameter-fragment synthetic
experiment command after M086A. Any M087R run remains future-only and must pass
fresh gates plus explicit operator approval.
