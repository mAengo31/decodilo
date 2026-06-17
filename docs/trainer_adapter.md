# Trainer Adapter

Milestone 005 separates learner runtime behavior from local training behavior.
The learner process no longer owns fake-model training directly; it calls a
`TrainerAdapter`.

## Interface

The adapter boundary is defined in `src/decodilo/trainer/interface.py`.
Adapters initialize from run id, learner id, seed, optional restored state, and
typed config. They expose methods for local training, state fragments, global
update application, full-state checkpointing, state-byte estimation, and health.

## Current Adapter

`NumpyConvexTrainer` implements the existing synthetic objective:

```text
minimize ||W - W_target||^2
```

It is still CPU-only and numpy-only. It reports local steps and token counts
separately, and exposes deterministic state checksums.

## State Codec

Trainer state and fragments use stable JSON with dtype, shape, codec version,
and checksums. Deserialization rejects unknown codec versions and corrupted
checksums. Pickle is not used.

## Future PyTorch Trainer

A future `PyTorchTrainer` should implement the same interface without changing
syncer, transport, event-log, replay, budget, or report protocols. It should be
responsible for local MFU and model-specific state, while the runtime remains
responsible for process lifecycle, idempotency, checkpointing, and metrics.

## Token Accounting

The trainer owns token accounting for local work. The syncer decides which
tokens become useful by accepting fragments into committed global rounds.
Zero-token fragments remain rejected by current syncer policy.

## Named-State Requirements

Milestone 006 adds named tensor state. Trainers may keep whatever internal
format they need, but exported state must be CPU-portable and deterministic:

- tensor names are sorted before flattening
- dtype, shape, offset, length, and checksum are recorded
- fragments carry checksum metadata
- checkpoint payloads use stable JSON, not pickle
- torch tensors must be converted to CPU arrays before serialization

`NumpyConvexTrainer` now represents its vector as the named tensor `weights`
and flattens it for the existing syncer merge path.

## Future PyTorch Expectations

Future PyTorch trainers should implement `TrainerAdapter`, export state through
`NamedTensorState`, report token counts independently from local steps, and keep
distributed training concerns outside the syncer protocol. CUDA, NCCL, DDP, and
FSDP are not part of the current scaffold.

## Milestone 007 Torch Compatibility

`TinyTorchCausalLMTrainer` implements the same adapter and uses the named-state
path. It exposes explicit token counts, parameter count, nonfinite detection,
safe checkpoint payloads, and an optimizer policy that resets on global update.

The runtime still selects trainers by name and talks only to `TrainerAdapter`.
Requesting torch trainers without the optional torch extra must fail clearly
with an install hint; default installation and default tests must not require
torch.

## Milestone 008 Chunked State Boundary

Trainer implementations may expose large logical state through chunked
manifests or synthetic chunk sources as long as they preserve the adapter
contract: deterministic checksums, explicit token counts, safe checkpoint
payloads, and no pickle. Runtime and syncer code should continue to treat
trainer state as protocol data, not trainer-specific Python objects.
