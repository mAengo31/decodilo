# ADR 0001: System Boundaries

## Status

Accepted.

## Context

The first milestone needs to make Decoupled DiLoCo coordination mechanics
testable without accidentally creating cloud spend, credential handling, or a
partially correct distributed trainer.

## Decision

The scaffold contains local protocol models, learner state, syncer state,
event logging, replay, pricing parsing from local data, budget guarding, and a
CPU simulator. It excludes real provider APIs, real credentials, GPU execution,
and LLM model training.

## Consequences

The platform can test quorum, merge, staleness, replay, and budget invariants
cheaply. Future cloud work must preserve these boundaries until a separate
rollout step explicitly adds authenticated infrastructure.

