# Lambda Integrated DiLoCo Smoke

`dev integrated-diloco-smoke` is a local/offline bounded synthetic smoke that
combines the previously separate learner/syncer protocol smoke and
AdamW/Nesterov optimizer-fidelity smoke.

```bash
python -m decodilo.cli dev integrated-diloco-smoke \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-integrated-diloco-smoke.json
```

The command uses deterministic in-memory synthetic vectors only. It performs no
network access, package installation, data/model download, real training,
torch/GPU work, background service start, or remote command. It writes one
bounded JSON report.

The report may state
`optimization_fidelity=integrated_optimizer_protocol_smoke` only because the
same tiny learner update is routed through the local protocol/replay path and
linked to the AdamW-derived pseudo-gradient used by the Nesterov reference
check. It does not claim full DiLoCo training, parameter-fragment
synchronization, communication overlap, or quantized communication.

The command is intended as the next bounded remote integrated synthetic DiLoCo
experiment command after M084A. Any M085R run remains future-only and must pass
fresh gates plus explicit operator approval.
