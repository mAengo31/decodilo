# Lambda L3 Direct-TCP Runtime Design

## Goal

Prove the Decoupled DiLoCo learner/syncer runtime across separate Lambda instances using direct TCP networking, not SSH reverse tunnels.

## Topology

- `syncer`: one Lambda instance running `decodilo.cli syncer serve --host 0.0.0.0 --port 28080`.
- `learner-0`, `learner-1`: separate Lambda instances running `decodilo.cli learner run --host <syncer-public-ip> --port 28080`.
- Training path: `tiny_adamw` inner optimizer (`adamw`) and Nesterov outer optimizer.

## Firewall strategy

Lambda accounts start with SSH and ICMP only. L3 temporarily adds exactly two scoped TCP rules:

- source `<learner-0-ip>/32` to syncer port `28080`
- source `<learner-1-ip>/32` to syncer port `28080`

The runner records `firewall_before.json`, `firewall_applied.json`, and `firewall_audit.json`, then restores the original firewall rules in `finally` before instance teardown.

## Acceptance

- 3 distinct Lambda instances.
- Direct TCP probe from each learner instance to syncer public IP passes.
- At least one committed sync round.
- AdamW/Nesterov semantics present.
- Numeric Nesterov replay from event log passes.
- Syncer checkpoint optimizer state matches replay.
- Learner artifacts present for both learners.
- Final live instance count is zero.
- Firewall rules restored.

## Non-goals

- Not production scale.
- Not Pathway/op-layer complete.
- Not model-scale training.
