# Metrics Semantics

Milestone 005 makes update-delivery and token metrics explicit.

## Update Metrics

- `global_update_broadcasts`: committed global update events made available to
  learners. Usually one per committed sync round.
- `global_update_messages_sent`: per-learner update payload messages sent.
- `global_update_acks`: valid per-learner acknowledgements for sent update
  payloads.
- `duplicate_global_update_acks`: duplicate or unsolicited acknowledgements
  ignored for valid ack accounting.
- `missing_global_update_acks`: sent update payloads without a valid
  acknowledgement by report time.
- `learner_update_lag_current`: learner id to current global-version lag.
- `learner_update_lag_max`: max observed learner lag across the run.
- `learner_update_lag_avg`: current average learner lag.

Valid update acknowledgements must not exceed update messages sent. Duplicate
acks are separate and do not inflate `global_update_acks`.

## Token Metrics

- `total_tokens_processed`: tokens processed by learners as observed by syncer.
- `useful_tokens_accepted`: tokens accepted into committed global updates.
- `rejected_tokens`: tokens attached to rejected fragments.
- `stale_tokens`: tokens attached to stale rejected fragments.
- `wasted_tokens`: `total_tokens_processed - useful_tokens_accepted`.
- `goodput_ratio`: `useful_tokens_accepted / total_tokens_processed`.

## Cost Metrics

`cost_per_total_token` and `cost_per_useful_token` are distinct. When useful
tokens are less than or equal to total tokens, cost per useful token must be at
least cost per total token.

## Validation

`src/decodilo/runtime/metrics_validation.py` validates report metrics. Normal
local reports include:

```json
{"metric_validation": {"passed": true, "errors": []}}
```

Validation catches impossible token accounting, invalid goodput, update ack
over-counting, and committed-round/global-version inconsistencies.
