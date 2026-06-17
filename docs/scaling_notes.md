# Scaling Notes

The Milestone 003 transport is not a production scaling architecture. It is a
local correctness harness for protocol, idempotency, process lifecycle, replay,
and failure behavior.

## Not The Final Bottleneck Solution

JSONL-over-TCP on localhost is easy to inspect and test, but it is not meant to
solve high-throughput WAN training coordination. It keeps dependencies small
while the system proves distributed correctness locally.

## Future Syncer Topology

Production scale will likely need sharded syncers, hierarchical aggregation, or
regional sync points. Those designs should preserve:

- stable idempotency keys
- deterministic event logs
- replay validation
- budget guards
- useful-token accounting

## Learner Training

Learner-local training should remain conventional and high-MFU once real models
exist. The WAN or cross-node control plane should carry outer-loop fragments and
metadata, not step-level gradients.

## Cloud Prerequisites

Before cloud scale, the system needs trainer adapter boundaries, idempotency,
replay, cost accounting, heartbeat semantics, update acknowledgement,
backpressure, learner and syncer checkpoint/recovery, fresh price provenance,
RunSpec/artifact manifests, and budget controls. Milestone 005 adds those checks
across local process boundaries without spending money.

## Planning Estimators

The scaling estimators model parameter bytes, optimizer state bytes, outer-loop
WAN bandwidth, checkpoint storage, run cost, and cost per useful token. They are
deliberately deterministic and offline.

Use them to identify obvious budget, bandwidth, checkpoint-retention, or low
goodput risks before adding GPU trainers or cloud launchers.

## Milestone 006 Planning Boundary

Named tensor fragmentation makes trainer state less toy-like, but the local
syncer still merges flat outer-loop fragments. The Lambda dry-run planner adds
auditable launch plans and capacity estimates, but it deliberately cannot
launch. Production scale still needs explicit launcher design, live availability
checks, sharded syncer planning, and larger soak evidence.

## Milestone 007 Compatibility Boundary

The tiny torch causal-LM trainer is a compatibility surface, not a performance
or quality benchmark. It exercises LLM-like parameter naming, token accounting,
safe state export/import, optimizer policy, and global update application while
remaining CPU-only and single-process per learner.

The disabled launcher interface and launch review checklist define the future
cloud boundary, but real Lambda launch remains unavailable. Before multi-GPU or
cloud training, the project still needs a production trainer, larger soak
evidence, live capacity checks, secure credential flow, launch supervision,
teardown verification, and scaling tests beyond localhost.

## Milestone 008 Large-State Boundary

The new chunk store, synthetic large-state source, streaming merge helper, and
memory-budget/spill policies make large-state failure modes testable without
allocating a real multi-billion-parameter model. These are readiness checks,
not a production sharded trainer.

Before cloud scale, the project still needs sharded numeric merge, remote
artifact storage, live capacity and availability checks, production checkpoint
retention policy, and end-to-end tests with real trainer state sizes.

## Milestone 009 Live Chunked Boundary

Live chunked payloads prove artifact-referenced learner submissions, global
updates, streaming numeric merge for small fragments, and chunked primary syncer
recovery on a shared local filesystem. This is still not a WAN/object-store
design. Production scale still needs remote artifact transport, sharded merge,
authn/authz around artifact access, retention policy, and failure tests across
real network boundaries.
