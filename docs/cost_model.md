# Cost Model

The scaffold treats cost as a first-class training metric. Raw GPU rental price
is useful, but it is not enough to compare distributed training runs.

## Raw GPU Cost

Raw GPU cost is the provider price for accelerator time, usually expressed as
price per GPU-hour or price per instance-hour.

```text
cluster_hourly_cost = instances * price_per_instance_hour
```

Example with an 8x H100 SXM instance:

```text
price_per_gpu_hour = 2.49
gpus_per_instance = 8
price_per_instance_hour = 2.49 * 8 = 19.92
planned_hours = 10
base_estimated_cost = 19.92 * 10 = 199.20
```

If the selected price file instead says `price_per_gpu_hour = 3.99`, the same
shape and duration becomes:

```text
price_per_instance_hour = 3.99 * 8 = 31.92
base_estimated_cost = 31.92 * 10 = 319.20
```

The CLI prints both price units and the source timestamp so this difference is
visible.

When a versioned price snapshot is used, the CLI also prints `snapshot_id` and
`record_id`. That makes the arithmetic traceable to exact source data rather
than an implicit constant.

## GPU-Hours

GPU-hours are the number of GPUs multiplied by elapsed hours.

```text
gpu_hours = gpus_per_instance * instances * hours
```

## Tokens

Accepted tokens are tokens from learner updates that make it into committed
sync rounds.

Useful tokens are accepted tokens that contribute to global progress. In this
scaffold, accepted tokens and useful tokens are equivalent.

Wasted tokens are tokens processed by learners but rejected or never committed.
Common causes include staleness, failure, and budget stop conditions.

```text
wasted_tokens = total_tokens_processed - useful_tokens
```

## Goodput

Goodput measures the share of processed tokens that become useful global work.

```text
goodput = useful_tokens / total_tokens_processed
```

Goodput is more useful than raw throughput for decentralized training because a
fast learner can still waste budget if its updates arrive stale.

## Effective Cost Per Useful Token

Effective cost per useful token divides actual spend by useful tokens:

```text
effective_cost_per_useful_token = actual_cost / useful_tokens
```

This metric combines provider price, cluster size, failures, stragglers, quorum
policy, and merge acceptance. It is the primary cost lens for future DiLoCo
experiments.

## Safety Buffer

The budget guard applies a safety buffer before checking available credits:

```text
safety_buffer_amount = base_estimated_cost * safety_buffer_pct
safety_buffer_adjusted_cost = base_estimated_cost + safety_buffer_amount
projected_remaining_credits =
  credits - committed_spend - observed_spend - safety_buffer_adjusted_cost
```

The default safety buffer is 15 percent. A run fails closed if the base estimate
exceeds `max_run_budget` or if the safety-buffer-adjusted cost would make
remaining credits negative.

## Price Freshness And Provenance

Price fixtures are sample data. They are acceptable for tests and examples, but
not as planning truth for cloud-intended runs. Snapshot-backed budget estimates
reject sample data and stale snapshots by default. The default stale threshold is
7 days.

Every snapshot records source type, source SHA-256, capture time, parser
version, tax flag, and normalized record ids. A future cloud run must have a
budget manifest identifying the selected snapshot, records, planned GPU-hours,
base cost, safety-buffer-adjusted cost, and projected remaining credits before
launch.

## Why Price Per GPU-Hour Is Not Enough

Two runs can have the same price per GPU-hour and very different value:

- A low-failure run can accept most tokens into global syncs.
- A high-staleness run can burn the same GPU-hours while rejecting many tokens.
- A quorum policy with no grace window can move quickly but waste late learner
  work.
- A large grace window can improve useful-token inclusion while slowing commit
  cadence.

The platform therefore tracks both raw spend and useful-token economics.

Example:

```text
run_a_cost = 100.00
run_a_total_tokens = 1,000,000
run_a_useful_tokens = 900,000
run_a_cost_per_useful_token = 0.000111...

run_b_cost = 100.00
run_b_total_tokens = 1,000,000
run_b_useful_tokens = 500,000
run_b_cost_per_useful_token = 0.0002
```

Both runs paid the same raw GPU price and processed the same total tokens, but
run B wasted more local work and is materially more expensive per useful token.

## Large-State Artifact Cost Pressure

Milestone 008 still performs no cloud launch, but it makes artifact volume
visible. Large model state changes cost planning through:

- checkpoint storage bytes
- checkpoint write bandwidth
- spill-to-disk volume during local/runtime pressure
- outer-loop fragment transfer bytes
- optimizer-state multiplier, which can exceed raw parameter bytes

Future cloud estimates should treat storage and transfer pressure as separate
warnings from raw GPU-hour price. A run with acceptable GPU-hour cost can still
be operationally unsafe if checkpoint retention, spill volume, or outer-loop
bandwidth exceeds the configured resource limits.
