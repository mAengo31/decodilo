# Lambda L1 AdamW/Nesterov Runtime Evidence

This directory persists the copied artifacts from the single-instance Lambda L1 verification run.

- Historical instance: `1bada235b1e5447d8bfbf2dd1b2c2309` (`gpu_1x_a10`, `us-east-1`).
- Runtime proof: one Lambda machine running the local learner/syncer runtime with two local learners and one syncer.
- Optimizers: inner `adamw`, outer `nesterov`.
- Committed rounds: 9.
- Independent numeric Nesterov re-derivation: passed with max absolute error 0.0.
- Final live instance count recorded after teardown: 0.

Boundary: this is not multi-instance distributed Lambda, not production scale, and not Pathway/op-layer readiness.
The parser/package builder is offline and performs no Lambda API calls.
