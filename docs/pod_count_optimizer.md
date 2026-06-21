# Pod Count Optimizer

The pod-count optimizer evaluates candidate learner counts and produces an explainable
recommendation.

Supported objectives:

- `minimize_cost_per_adjusted_token`
- `maximize_useful_tokens_per_second`
- `minimize_wall_clock_time`
- `minimize_cost_per_useful_token`
- `stay_under_bandwidth_cap`

Each candidate includes raw, accepted, useful, and sample-efficiency-adjusted token
rates; cost per token; artifact/backend pressure; syncer pressure; bandwidth pressure;
dominant bottleneck; warnings; and rejection status.

Candidates that exceed configured hard caps are rejected. If every candidate is rejected,
the optimizer returns no recommendation and explains why.

Example:

```bash
python -m decodilo.cli scaling optimize-pods \
  --scenario-json /tmp/scenario.json \
  --objective minimize_cost_per_adjusted_token \
  --out /tmp/decodilo-pod-optimization.json
```

