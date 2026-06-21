# Goodput Model

The goodput model distinguishes raw allocation from useful accepted training work:

- `raw_availability`: expected per-learner availability after failure, recovery,
  startup, and preemption loss.
- `quorum_availability`: probability that at least `min_quorum` learners are usable.
- `accepted_contribution_ratio`: useful contribution accepted by the syncer after
  quorum and straggler effects.
- `straggler_loss_ratio`: speed variance penalty after any grace-window relief.
- `recovery_loss_ratio`: time lost to ordinary failures and recovery.
- `preemption_loss_ratio`: time lost to preemption and restart.
- `estimated_goodput_ratio`: planning ratio for useful active learner contribution.

Analytic estimates are deterministic. A fixed-seed Monte Carlo estimator is also
available for validation. The model is planning-only and does not claim paper-level
DiLoCo convergence results.

