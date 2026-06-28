# Lambda L4 Multi-Round Direct-TCP Runtime Design

## Goal

Extend L3 from a one-round direct-TCP proof to a multi-round direct-TCP proof across separate Lambda instances.

## Change from L3

L3 proved direct TCP worked after scoped firewall rules were applied, but only committed one round because one learner completed before the other learner arrived and before subsequent quorum windows.

L4 keeps the same direct-TCP topology and temporary firewall strategy, but runs learners longer and slower:

- `steps=200`
- `step_delay_seconds=0.05`
- `local_steps_per_sync=1`

This keeps both learners alive long enough to receive global updates and contribute to multiple quorum commits.

## Acceptance

- 3 distinct Lambda instances.
- direct TCP probe from each learner instance to syncer public IP passes.
- temporary firewall rules are restored to the exact pre-run rules.
- `committed_sync_rounds >= 2`.
- AdamW/Nesterov semantics are present.
- numeric Nesterov replay passes.
- final live instance count is zero.

## Non-goals

- Not production scale.
- Not Pathway/op-layer complete.
- Not model-scale training.
