# ADR 0002: CPU Simulator First

## Status

Accepted.

## Context

Distributed training failures are expensive to diagnose when correctness is
not already observable. GPU experiments also make test results sensitive to
hardware availability and provider behavior.

## Decision

The first scaffold uses a toy CPU vector model and deterministic logical time.
The model optimizes `||W - W_target||^2`; it is not a proxy for LLM quality.

## Consequences

The simulator can run in CI and local development. It validates synchronization
mechanics before any cloud launch or GPU dependency exists.

