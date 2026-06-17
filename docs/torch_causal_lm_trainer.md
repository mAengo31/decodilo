# Tiny Torch Causal LM Trainer

Milestone 007 adds `TinyTorchCausalLMTrainer` as an optional PyTorch trainer
adapter. It exists to exercise LLM-shaped trainer surfaces without requiring
GPUs, CUDA, NCCL, distributed PyTorch, external datasets, or tokenizers.

## Optional Dependency

The default install does not depend on PyTorch. Install the optional extra only
for local compatibility testing:

```bash
pip install -e '.[torch]'
```

Torch is imported lazily through `torch_optional.require_torch()`. Importing
`decodilo` or the syncer does not import torch.

## Model Shape

The trainer is intentionally tiny and CPU-first. It includes:

- token embeddings
- positional embeddings
- optional causal self-attention blocks
- a final layer norm
- an LM head
- next-token cross entropy on deterministic synthetic tokens

The defaults are small, and tests use even smaller CPU shapes. This is not a
production LLM trainer and is not a quality benchmark.

## Training And Tokens

`train_local_steps(n)` reports local steps and tokens separately. For the
causal LM path:

```text
tokens_processed = batch_size * seq_len * local_steps_completed
```

Loss, gradient norm, parameter count, and nonfinite detection are reported when
available. NaN or Inf loss, gradient norm, or parameters raise an invariant
failure.

## State Export And Global Updates

Parameters are exported as `NamedTensorState`, converted to flat fragments, and
merged by the existing syncer path. The syncer still sees numeric flat
fragments; the trainer owns reconstruction into named tensors.

`apply_global_update()` reconstructs the named tensor state for the current
module shape, strictly checks tensor names and shapes, loads parameters, sets
the applied global version, and resets optimizer state by default.

## Optimizer Policy

The default optimizer is SGD. The current policy is:

```text
reset_on_global_update = true
serialized_optimizer_state_supported = false
```

AdamW can be selected for local experiments, but serialized AdamW tensor state
is not implemented in this milestone. Checkpoint payloads record the optimizer
policy and fail closed if serialized tensor state is incorrectly claimed as
supported.

## Checkpoint And Restore

Checkpoint payloads use the existing JSON/checksum trainer state codec. They
include trainer config metadata, model parameters, local step, token counters,
applied global version, optimizer policy, and state checksum. No `torch.save`,
pickle, or arbitrary code execution is used.

## Limitations

- CPU-only compatibility surface.
- No DDP, FSDP, torchrun, NCCL, CUDA requirement, or multi-GPU behavior.
- No tokenizer or external dataset.
- No real transformer scale.
- No production optimizer-state serialization.

