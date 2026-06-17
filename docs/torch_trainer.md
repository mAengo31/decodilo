# Optional Torch Trainer

Milestone 006 adds an optional PyTorch trainer adapter path without making
PyTorch a default dependency.

Install the optional extra only when you want to exercise the torch trainer:

```bash
pip install -e '.[torch]'
```

The default install and default test suite do not require torch, CUDA, NCCL, or
GPUs.

## Lazy Import

`src/decodilo/trainer/torch_optional.py` exposes:

- `torch_available()`
- `require_torch()`

The package does not import torch at module import time. Selecting
`trainer_type=torch_tiny` is what triggers the optional import.

## Tiny Torch Trainer

`TinyTorchMLPTrainer` is a small CPU-capable adapter used to test the trainer
boundary. It is not an LLM trainer and does not use distributed PyTorch.

It:

- runs on `device="cpu"` by default
- uses deterministic synthetic data
- reports local steps and tokens separately
- exports state through `NamedTensorState`
- checkpoints through stable JSON checksums, not `torch.save`
- applies global updates through the same flat-fragment path as numpy

CUDA may be requested only explicitly and only when `torch.cuda.is_available()`
is true. This milestone does not use DDP, FSDP, NCCL, torchrun, or GPUs.

## Tiny Causal LM Trainer

Milestone 007 adds `TinyTorchCausalLMTrainer`. It is still optional and
CPU-first, but it is LLM-shaped enough to exercise token embeddings,
positional embeddings, causal context, LM-head logits, cross-entropy next-token
loss, named-state export/import, optimizer reset policy, and safe
checkpoint/restore.

It is not a real LLM training loop. It has no distributed torch path, no
external data, no tokenizer, no CUDA requirement, and no cloud execution path.
The default optimizer policy resets optimizer state on every global update.

## Safe State

Torch tensors are converted to CPU numpy arrays before serialization. The state
codec records dtype, shape, tensor manifest, and checksums. No pickle or
arbitrary code execution is used for transported or checkpointed state.
