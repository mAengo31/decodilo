# ADR 0003: Cost Per Useful Token

## Status

Accepted.

## Context

Price per GPU-hour does not account for rejected stale updates, failed learners,
or quorum policies that waste local work.

## Decision

The scaffold tracks useful tokens accepted into committed sync rounds and
exposes effective cost per useful token:

```text
actual_cost / useful_tokens
```

## Consequences

Future experiments can compare useful training work, not just raw accelerator
time. Budget guards can fail closed before a run starts, and replay can verify
accepted useful-token counts after the fact.

