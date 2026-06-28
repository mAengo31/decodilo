# Lambda L2 Remote AdamW/Nesterov Runtime Design

## Objective

Prove the minimal Decoupled DiLoCo runtime path across multiple Lambda instances, not merely local-loopback on one machine.

## L2 topology

- 1 syncer instance: runs `decodilo.cli syncer serve` bound to `0.0.0.0:<port>`.
- 2 learner instances: each runs one `decodilo.cli learner run` process that connects over TCP to the syncer instance IP/port.
- Runtime mechanics: `tiny_adamw` trainer, inner optimizer `adamw`, outer optimizer `nesterov`, CPU-only synthetic data, inline payloads.
- Acceptance: at least one committed round, numeric Nesterov replay from event log passes, syncer checkpoint optimizer state matches replay, learner logs/checkpoints exist on both learner instances.

## Non-goals

- No model-scale training claim.
- No production-scale claim.
- No Pathway/op-layer claim.
- No GPU utilization claim; Lambda GPU instances are used only as available remote compute hosts.

## Safety

The L2 runner must:

1. launch only owned instances for the run,
2. record every owned instance id,
3. terminate all owned instances in `finally`,
4. perform a final read-only instance check,
5. persist evidence under `docs/evidence/lambda_l2_remote_adamw_nesterov/<run_id>/`,
6. keep `launch_ready=false` and `launch_allowed=false` in evidence packages.

## Expected evidence files

- `layout.json`
- `termination_safety.json`
- `syncer/events.jsonl`
- `syncer/syncer_checkpoint.json`
- `syncer/syncer_summary.json`
- `syncer/syncer.stdout`, `syncer/syncer.stderr`
- `learner-0/learner-0.checkpoint.json`, `learner-0/learner-0.log`, stdout/stderr
- `learner-1/learner-1.checkpoint.json`, `learner-1/learner-1.log`, stdout/stderr
- `lambda_l2_evidence_package.json`
