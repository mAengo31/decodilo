# Scaling Model

The scaling estimators are deterministic calculators for planning before any
credit spend.

## Model State

Parameter bytes are:

```text
parameter_bytes = parameter_count * bytes_per_parameter
```

Optimizer state is estimated with a multiplier:

```text
optimizer_state_bytes =
  parameter_count * bytes_per_parameter * optimizer_multiplier
```

Total model state is parameter bytes plus optimizer state bytes.

## Fragments And Bandwidth

The bandwidth estimator models outer-loop fragment exchange, not step-level
gradients. It estimates full model bytes, fragment bytes, bytes per sync round,
aggregate sync traffic, average bandwidth, and a simple peak estimate.

Compression bits reduce effective bytes per parameter. More learners increase
aggregate traffic. Longer sync intervals reduce average bandwidth.

## Checkpoint Storage

Checkpoint estimates include:

- global checkpoint size
- learner checkpoint size
- retained checkpoint storage
- write bandwidth required for the configured interval

Retention increases total storage linearly.

## Cost Projection

Cost projection combines instance-hour price, planned hours, expected goodput,
and expected useful tokens. Cost per useful token rises when goodput drops,
even when raw instance-hour price is unchanged.

## Capacity Plan

The capacity planner combines a price snapshot record, model size, sync
interval, learner count, expected token rate, expected goodput, planned hours,
and credit budget. It returns JSON-serializable estimates and warnings for
budget pressure, low goodput, and high average bandwidth.

These estimates are planning aids, not training-quality predictions.

## Cloud Dry-Run Integration

Milestone 006 can embed capacity planning output in a Lambda dry-run report when
parameter count, bytes per parameter, expected token rate, goodput, sync
interval, and compression fields are supplied.

Compression lowers the estimated outer-loop bandwidth. Lower goodput raises
expected cost per useful token for fixed raw spend.

## Large-State Memory And Checkpoint Pressure

Milestone 008 adds a `scaling large-state` command for quick pressure checks.
It combines parameter bytes, optimizer-state multiplier, chunk size, learner
count, and memory budget to estimate:

- parameter count
- parameter bytes
- optimizer multiplier
- optimizer-state bytes
- total state bytes
- chunk size in bytes
- estimated chunk count
- memory budget in bytes
- whether the state fits in memory
- whether spill/chunking is required
- aggregate learner state bytes
- whether the configured memory budget is obviously insufficient

The optimizer multiplier matters: Adam-style state can require multiple extra
copies of parameter-sized tensors. Checkpoint storage and write bandwidth should
be planned from total model state, not just raw parameter bytes.

Example:

```bash
python -m decodilo.cli scaling large-state \
  --params 7000000000 \
  --bytes-per-param 2 \
  --optimizer-multiplier 2 \
  --chunk-size-mb 64 \
  --memory-budget-mb 1024 \
  --learners 8
```

Arithmetic:

```text
parameter_bytes = 7,000,000,000 * 2 = 14,000,000,000
optimizer_state_bytes = parameter_bytes * 2 = 28,000,000,000
total_state_bytes = 42,000,000,000
chunk_size_bytes = 64 * 1024 * 1024
```

If `total_state_bytes <= memory_budget_bytes`, `fits_in_memory=true` and
`spill_required=false`. Otherwise, `fits_in_memory=false` and
`spill_required=true`.

## Learner Pod Scaling

Milestone 014A adds learner-pod scaling estimates for fixed total compute,
expanding compute, and scavenged compute. The model evaluates candidate learner
counts against:

- failure and recovery availability
- quorum availability
- accepted contribution ratio
- artifact read/write pressure
- WAN bandwidth pressure
- syncer merge pressure
- heuristic algorithmic efficiency
- cost per useful token
- cost per sample-efficiency-adjusted token

The optimizer produces a recommendation only when configured bandwidth,
artifact, and syncer caps are not exceeded. Backend design targets in the report
are planning targets for a future remote artifact backend; they are not a remote
backend validation.
