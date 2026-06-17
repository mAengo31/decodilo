# Lambda Rollout Plan

This scaffold is deliberately offline. It must not call Lambda Cloud APIs, use
real credentials, launch instances, or spend money.

## Stage 0: Local Correctness

- Run the CPU simulator and replay tests.
- Verify quorum, grace-window, staleness, failure, pricing, and budget guard
  invariants.
- Keep all pricing inputs as local data snapshots or reviewed static JSON.
- Do not perform any cloud launch until tests pass.

## Stage 1: Cheap Validation Target

The first Lambda target should be a cheap validation path, not H100-scale
training. The goal is to validate packaging, bootstrapping, logging, and budget
guards with minimal risk.

Requirements before this stage:

- explicit user approval
- reviewed static price file
- max run budget
- safety buffer
- dry-run output showing projected remaining credits
- no secrets committed to the repository

## Stage 2: Local Multi-Process Correctness

Before using A100 or H100 instances, add a local multi-process transport that
preserves the same protocol and event log. The system should prove:

- learner lifecycle events remain deterministic enough for replay
- syncer decisions are serializable
- stale updates are rejected consistently
- checkpoints can be restored without hidden process state

## Stage 3: Small Cloud Smoke Test

Use only a budget-capped smoke test. This stage should validate:

- instance boot and teardown
- artifact upload and download
- event log collection
- checkpoint write and restore
- observed spend tracking

Abort if projected remaining credits go negative after safety buffer.

## Stage 4: A100/H100 Experiments

Use A100 or H100 only after CPU and local multi-process correctness have been
verified. Treat pricing assumptions as data, not hardcoded truth. Refresh the
price snapshot, commit the static JSON used for the run, and include its source
timestamp in the run metadata.

Each launch must include:

- max run budget
- cluster hourly cost
- max hours allowed by credits
- safety buffer
- expected useful-token target
- stop condition for low goodput

