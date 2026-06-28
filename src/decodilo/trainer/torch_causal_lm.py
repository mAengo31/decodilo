"""Optional tiny LLM-shaped PyTorch trainer adapter."""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.trainer.eval import EvalResult
from decodilo.trainer.flattening import (
    flatten_named_state,
    fragment_flat_state,
    make_fragment_layout,
)
from decodilo.trainer.named_state import NamedTensorState
from decodilo.trainer.state import (
    TrainerConfig,
    TrainerFragment,
    TrainerHealth,
    TrainerState,
    TrainStepResult,
)
from decodilo.trainer.state_codec import decode_state, encode_state, make_fragment
from decodilo.trainer.synthetic_data import make_synthetic_token_batch
from decodilo.trainer.torch_metrics import (
    compute_grad_norm,
    module_has_nonfinite,
    module_num_parameters,
)
from decodilo.trainer.torch_optimizer_state import (
    OptimizerStatePolicy,
    make_optimizer_policy,
    safe_optimizer_checkpoint_payload,
)
from decodilo.trainer.torch_optional import require_torch
from decodilo.trainer.torch_state import (
    flat_vector_to_named_state_for_module,
    load_named_state_into_module,
    module_to_named_state,
)


def estimate_causal_lm_num_parameters(
    *,
    vocab_size: int = 64,
    seq_len: int = 16,
    d_model: int = 32,
    num_layers: int = 1,
    mlp_ratio: float = 2.0,
) -> int:
    """Return the parameter count for the tiny causal-LM architecture."""

    hidden = int(round(d_model * mlp_ratio))
    embeddings = vocab_size * d_model + seq_len * d_model
    per_layer = 4 * d_model * d_model + 2 * d_model * hidden + 9 * d_model + hidden
    final_ln = 2 * d_model
    lm_head = vocab_size * d_model
    return int(embeddings + num_layers * per_layer + final_ln + lm_head)


def _torch_dtype(torch: Any, dtype: str):
    if dtype == "float32":
        return torch.float32
    if dtype == "float64":
        return torch.float64
    raise InvariantViolation(f"unsupported torch dtype {dtype!r}")


def _build_model(
    *,
    vocab_size: int,
    seq_len: int,
    d_model: int,
    num_layers: int,
    num_heads: int,
    mlp_ratio: float,
    dtype: str,
    device: str,
):
    torch = require_torch()
    nn = torch.nn

    if d_model % num_heads != 0:
        raise InvariantViolation("d_model must be divisible by num_heads")
    hidden = int(round(d_model * mlp_ratio))
    torch_dtype = _torch_dtype(torch, dtype)

    class TinyBlock(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.ln1 = nn.LayerNorm(d_model)
            self.q_proj = nn.Linear(d_model, d_model)
            self.k_proj = nn.Linear(d_model, d_model)
            self.v_proj = nn.Linear(d_model, d_model)
            self.out_proj = nn.Linear(d_model, d_model)
            self.ln2 = nn.LayerNorm(d_model)
            self.fc1 = nn.Linear(d_model, hidden)
            self.fc2 = nn.Linear(hidden, d_model)

        def forward(self, x):  # noqa: ANN001, ANN202 - local torch module
            batch, tokens, channels = x.shape
            head_dim = channels // num_heads
            normalized = self.ln1(x)
            q = self.q_proj(normalized).view(batch, tokens, num_heads, head_dim).transpose(1, 2)
            k = self.k_proj(normalized).view(batch, tokens, num_heads, head_dim).transpose(1, 2)
            v = self.v_proj(normalized).view(batch, tokens, num_heads, head_dim).transpose(1, 2)
            scores = (q @ k.transpose(-2, -1)) / math.sqrt(head_dim)
            mask = torch.triu(
                torch.ones(tokens, tokens, dtype=torch.bool, device=x.device),
                diagonal=1,
            )
            scores = scores.masked_fill(mask, torch.finfo(scores.dtype).min)
            attn = torch.softmax(scores, dim=-1)
            context = attn @ v
            context = context.transpose(1, 2).contiguous().view(batch, tokens, channels)
            x = x + self.out_proj(context)
            x = x + self.fc2(torch.relu(self.fc1(self.ln2(x))))
            return x

    class TinyCausalLM(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.token_embedding = nn.Embedding(vocab_size, d_model)
            self.position_embedding = nn.Embedding(seq_len, d_model)
            self.layers = nn.ModuleList([TinyBlock() for _ in range(num_layers)])
            self.final_ln = nn.LayerNorm(d_model)
            self.lm_head = nn.Linear(d_model, vocab_size, bias=False)

        def forward(self, input_ids):  # noqa: ANN001, ANN202 - local torch module
            positions = torch.arange(input_ids.shape[1], device=input_ids.device)
            x = self.token_embedding(input_ids) + self.position_embedding(positions)[None, :, :]
            for layer in self.layers:
                x = layer(x)
            return self.lm_head(self.final_ln(x))

    return TinyCausalLM().to(device=device, dtype=torch_dtype)


class TinyTorchCausalLMTrainer:
    """Small CPU-first causal-LM trainer implementing TrainerAdapter."""

    trainer_type = "torch_causal_lm"

    def __init__(self) -> None:
        self.torch = None
        self.module = None
        self.optimizer_obj = None
        self.optimizer_policy = make_optimizer_policy("sgd")
        self.run_id = ""
        self.learner_id = ""
        self.seed = 0
        self.global_version = 0
        self.local_step = 0
        self.tokens_processed = 0
        self.tokens_since_last_sync = 0
        self.last_applied_global_version = 0
        self.vocab_size = 64
        self.seq_len = 16
        self.batch_size = 4
        self.d_model = 32
        self.num_layers = 1
        self.num_heads = 2
        self.mlp_ratio = 2.0
        self.learning_rate = 0.05
        self.gradient_clip_norm: float | None = None
        self.device = "cpu"
        self.requested_device = "cpu"
        self.actual_device = "cpu"
        self.cuda_available = False
        self.dtype = "float32"
        self.last_loss: float | None = None
        self.last_eval_loss: float | None = None
        self.nonfinite_detected = False

    def initialize(
        self,
        *,
        run_id: str,
        learner_id: str,
        seed: int,
        initial_state: TrainerState | None,
        config: TrainerConfig,
    ) -> None:
        torch = require_torch()
        self.torch = torch
        self.run_id = run_id
        self.learner_id = learner_id
        self.seed = seed
        self.vocab_size = config.vocab_size
        self.seq_len = config.seq_len
        self.batch_size = config.batch_size
        self.d_model = config.d_model
        self.num_layers = config.num_layers
        self.num_heads = config.num_heads
        self.mlp_ratio = config.mlp_ratio
        self.learning_rate = config.learning_rate
        self.gradient_clip_norm = config.gradient_clip_norm
        self.device = config.device
        self.requested_device = config.device
        self.cuda_available = bool(torch.cuda.is_available())
        self.dtype = config.dtype
        self.optimizer_policy = make_optimizer_policy(config.optimizer)
        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise InvariantViolation("cuda device requested but torch.cuda is unavailable")
        torch.manual_seed(seed)
        self.module = _build_model(
            vocab_size=self.vocab_size,
            seq_len=self.seq_len,
            d_model=self.d_model,
            num_layers=self.num_layers,
            num_heads=self.num_heads,
            mlp_ratio=self.mlp_ratio,
            dtype=self.dtype,
            device=self.device,
        )
        self.actual_device = str(next(self.module.parameters()).device)
        self._reset_optimizer()
        if initial_state is not None:
            self.set_full_state(initial_state, global_version=initial_state.global_version)
            return
        if config.initial_vector is not None and any(
            float(value) != 0.0 for value in config.initial_vector
        ):
            state = flat_vector_to_named_state_for_module(
                self.module,
                values=[float(value) for value in config.initial_vector],
                global_version=0,
            )
            load_named_state_into_module(self.module, state)
        self.global_version = 0
        self.last_applied_global_version = 0
        self.local_step = 0
        self.tokens_processed = 0
        self.tokens_since_last_sync = 0
        self._guard_finite()

    def _reset_optimizer(self) -> None:
        torch = require_torch()
        assert self.module is not None
        if self.optimizer_policy.optimizer_name == "sgd":
            self.optimizer_obj = torch.optim.SGD(self.module.parameters(), lr=self.learning_rate)
        elif self.optimizer_policy.optimizer_name == "adamw":
            self.optimizer_obj = torch.optim.AdamW(self.module.parameters(), lr=self.learning_rate)
        else:
            raise InvariantViolation(
                f"unsupported optimizer {self.optimizer_policy.optimizer_name}"
            )

    def _batch(self, step: int):
        batch = make_synthetic_token_batch(
            run_id=self.run_id,
            learner_id=self.learner_id,
            seed=self.seed,
            local_step=step,
            batch_size=self.batch_size,
            seq_len=self.seq_len,
            vocab_size=self.vocab_size,
        )
        torch = require_torch()
        inputs = torch.tensor(batch.inputs, dtype=torch.long, device=self.device)
        targets = torch.tensor(batch.targets, dtype=torch.long, device=self.device)
        return batch, inputs, targets

    def _loss(self, inputs, targets):  # noqa: ANN001, ANN202 - torch tensors
        assert self.module is not None
        torch = require_torch()
        logits = self.module(inputs)
        return torch.nn.functional.cross_entropy(
            logits.reshape(-1, self.vocab_size),
            targets.reshape(-1),
        )

    def _guard_finite(self) -> None:
        assert self.module is not None
        if module_has_nonfinite(self.module):
            self.nonfinite_detected = True
            raise InvariantViolation("non-finite parameter detected")

    def train_local_steps(self, num_steps: int) -> TrainStepResult:
        if num_steps < 0:
            raise ValueError("num_steps must be non-negative")
        assert self.optimizer_obj is not None
        torch = require_torch()
        started = time.monotonic()
        previous_step = self.local_step
        previous_tokens = self.tokens_processed
        loss_before: float | None = None
        loss_after: float | None = None
        grad_norm: float | None = None
        for _ in range(num_steps):
            batch, inputs, targets = self._batch(self.local_step)
            self.optimizer_obj.zero_grad(set_to_none=True)
            loss = self._loss(inputs, targets)
            if not torch.isfinite(loss):
                self.nonfinite_detected = True
                raise InvariantViolation("non-finite loss detected")
            if loss_before is None:
                loss_before = float(loss.detach().cpu().item())
            loss.backward()
            grad_norm = compute_grad_norm(self.module)
            if grad_norm is not None and not math.isfinite(grad_norm):
                self.nonfinite_detected = True
                raise InvariantViolation("non-finite gradient norm detected")
            if self.gradient_clip_norm is not None:
                torch.nn.utils.clip_grad_norm_(self.module.parameters(), self.gradient_clip_norm)
                grad_norm = compute_grad_norm(self.module)
            self.optimizer_obj.step()
            with torch.no_grad():
                loss_after_tensor = self._loss(inputs, targets)
            if not torch.isfinite(loss_after_tensor):
                self.nonfinite_detected = True
                raise InvariantViolation("non-finite post-step loss detected")
            loss_after = float(loss_after_tensor.detach().cpu().item())
            self.local_step += 1
            self.tokens_processed += batch.token_count
            self.tokens_since_last_sync += batch.token_count
            self.last_loss = loss_after
            self._guard_finite()
        return TrainStepResult(
            local_steps=self.local_step - previous_step,
            local_steps_completed=self.local_step - previous_step,
            tokens_processed=self.tokens_processed - previous_tokens,
            tokens_since_last_sync=self.tokens_since_last_sync,
            loss=loss_after,
            loss_before=loss_before,
            loss_after=loss_after,
            final_loss=loss_after,
            grad_norm=grad_norm,
            num_parameters=self.num_parameters,
            wall_time_seconds=time.monotonic() - started,
        )

    @property
    def num_parameters(self) -> int:
        assert self.module is not None
        return module_num_parameters(self.module)

    def get_named_state(self) -> NamedTensorState:
        assert self.module is not None
        return module_to_named_state(self.module, global_version=self.global_version)

    def get_state_fragments(self, fragment_ids: list[int] | None = None) -> list[TrainerFragment]:
        named_state = self.get_named_state()
        flat_state = flatten_named_state(named_state)
        layout = make_fragment_layout(total_elements=len(flat_state.values), num_fragments=1)
        flat_fragment = fragment_flat_state(flat_state, layout)[0]
        fragment = make_fragment(
            trainer_type=self.trainer_type,
            run_id=self.run_id,
            learner_id=self.learner_id,
            fragment_id=flat_fragment.fragment_id,
            global_version=self.global_version,
            data=np.asarray(flat_fragment.data, dtype=np.float64),
            tokens=self.tokens_since_last_sync,
            metadata={
                "trainer_state_kind": "named_tensors",
                "flat_state_checksum": flat_state.checksum,
                "named_state_checksum": named_state.checksum,
                "optimizer": self.optimizer_policy.optimizer_name,
                "optimizer_policy": self.optimizer_policy.model_dump(mode="json"),
                "optimizer_state": {"present": self.optimizer_obj is not None},
                "real_training_mechanics_exercised": self.local_step > 0,
                "real_model_training_claimed": True,
                "paper_scale_training_claimed": False,
            },
            trainer_state_kind="named_tensors",
            flat_fragment=flat_fragment.model_dump(mode="json"),
            tensor_manifest=flat_state.manifest.model_dump(mode="json"),
        )
        if fragment_ids is not None and 0 not in fragment_ids:
            return []
        return [fragment]

    def apply_global_update(
        self,
        fragments: list[TrainerFragment],
        *,
        global_version: int,
    ) -> None:
        if global_version < self.global_version:
            raise InvariantViolation("trainer global version cannot move backwards")
        if not fragments:
            return
        assert self.module is not None
        values = [
            value
            for fragment in sorted(fragments, key=lambda item: item.fragment_id)
            for value in fragment.data
        ]
        state = flat_vector_to_named_state_for_module(
            self.module,
            values=[float(value) for value in values],
            global_version=global_version,
        )
        load_named_state_into_module(self.module, state)
        self.global_version = global_version
        self.last_applied_global_version = global_version
        if self.optimizer_policy.reset_on_global_update:
            self._reset_optimizer()
        self._guard_finite()

    def _metadata(self) -> dict[str, Any]:
        return {
            "vocab_size": self.vocab_size,
            "seq_len": self.seq_len,
            "batch_size": self.batch_size,
            "d_model": self.d_model,
            "num_layers": self.num_layers,
            "num_heads": self.num_heads,
            "mlp_ratio": self.mlp_ratio,
            "learning_rate": self.learning_rate,
            "gradient_clip_norm": self.gradient_clip_norm,
            "device": self.device,
            "requested_device": self.requested_device,
            "actual_device": self.actual_device,
            "cuda_available": self.cuda_available,
            "dtype": self.dtype,
            "seed": self.seed,
            "last_loss": self.last_loss,
            "last_eval_loss": self.last_eval_loss,
            "last_applied_global_version": self.last_applied_global_version,
            "optimizer": self.optimizer_policy.optimizer_name,
            "optimizer_policy": self.optimizer_policy.model_dump(mode="json"),
            "optimizer_state": {"present": self.optimizer_obj is not None},
            "real_training_mechanics_exercised": self.local_step > 0,
            "real_model_training_claimed": True,
            "paper_scale_training_claimed": False,
            "num_parameters": self.num_parameters,
        }

    def get_full_state(self) -> TrainerState:
        named_state = self.get_named_state()
        flat_state = flatten_named_state(named_state)
        from decodilo.trainer.state_codec import make_state

        return make_state(
            trainer_type=self.trainer_type,
            run_id=self.run_id,
            learner_id=self.learner_id,
            global_version=self.global_version,
            local_step=self.local_step,
            tokens_processed=self.tokens_processed,
            tokens_since_last_sync=self.tokens_since_last_sync,
            parameters=np.asarray(flat_state.values, dtype=np.float64),
            metadata=self._metadata(),
            trainer_state_kind="named_tensors",
            tensor_manifest=flat_state.manifest.model_dump(mode="json"),
            flat_state_checksum=flat_state.checksum,
            named_state_checksum=named_state.checksum,
        )

    def set_full_state(self, state: TrainerState, *, global_version: int) -> None:
        metadata = state.metadata
        self.vocab_size = int(metadata.get("vocab_size", self.vocab_size))
        self.seq_len = int(metadata.get("seq_len", self.seq_len))
        self.batch_size = int(metadata.get("batch_size", self.batch_size))
        self.d_model = int(metadata.get("d_model", self.d_model))
        self.num_layers = int(metadata.get("num_layers", self.num_layers))
        self.num_heads = int(metadata.get("num_heads", self.num_heads))
        self.mlp_ratio = float(metadata.get("mlp_ratio", self.mlp_ratio))
        self.learning_rate = float(metadata.get("learning_rate", self.learning_rate))
        self.gradient_clip_norm = metadata.get("gradient_clip_norm", self.gradient_clip_norm)
        self.device = str(metadata.get("device", self.device))
        self.requested_device = str(metadata.get("requested_device", self.device))
        self.actual_device = str(metadata.get("actual_device", self.device))
        self.cuda_available = bool(metadata.get("cuda_available", False))
        self.dtype = str(metadata.get("dtype", self.dtype))
        self.seed = int(metadata.get("seed", self.seed))
        optimizer_policy = metadata.get("optimizer_policy")
        if optimizer_policy:
            self.optimizer_policy = OptimizerStatePolicy.model_validate(optimizer_policy)
        self.run_id = state.run_id
        self.learner_id = state.learner_id
        torch = require_torch()
        self.torch = torch
        self.module = _build_model(
            vocab_size=self.vocab_size,
            seq_len=self.seq_len,
            d_model=self.d_model,
            num_layers=self.num_layers,
            num_heads=self.num_heads,
            mlp_ratio=self.mlp_ratio,
            dtype=self.dtype,
            device=self.device,
        )
        self.cuda_available = bool(torch.cuda.is_available())
        self.actual_device = str(next(self.module.parameters()).device)
        named = flat_vector_to_named_state_for_module(
            self.module,
            values=[float(value) for value in state.parameters],
            global_version=global_version,
        )
        load_named_state_into_module(self.module, named)
        self._reset_optimizer()
        self.global_version = global_version
        self.last_applied_global_version = int(
            metadata.get("last_applied_global_version", global_version)
        )
        self.local_step = state.local_step
        self.tokens_processed = state.tokens_processed
        self.tokens_since_last_sync = state.tokens_since_last_sync
        self.last_loss = metadata.get("last_loss")
        self.last_eval_loss = metadata.get("last_eval_loss")
        self._guard_finite()

    def checkpoint_payload(self) -> dict[str, Any]:
        payload = {
            "trainer_config": self._metadata(),
            "trainer_state": encode_state(self.get_full_state()),
            **safe_optimizer_checkpoint_payload(self.optimizer_policy),
        }
        return payload

    def restore_from_checkpoint(self, payload: dict[str, Any]) -> None:
        policy_payload = payload.get("optimizer_policy")
        if policy_payload is not None:
            self.optimizer_policy = OptimizerStatePolicy.model_validate(policy_payload)
        state = decode_state(str(payload["trainer_state"]))
        self.set_full_state(state, global_version=state.global_version)

    def estimate_state_bytes(self) -> int:
        return int(
            sum(
                tensor.detach().cpu().numpy().nbytes
                for tensor in self.module.state_dict().values()
            )
        )

    def evaluate(self, *, eval_steps: int = 2) -> EvalResult:
        assert self.module is not None
        torch = require_torch()
        losses: list[float] = []
        tokens = 0
        with torch.no_grad():
            for index in range(eval_steps):
                batch, inputs, targets = self._batch(1_000_000 + index)
                loss = self._loss(inputs, targets)
                if not torch.isfinite(loss):
                    self.nonfinite_detected = True
                    raise InvariantViolation("non-finite eval loss detected")
                losses.append(float(loss.detach().cpu().item()))
                tokens += batch.token_count
        eval_loss = float(sum(losses) / len(losses)) if losses else 0.0
        return EvalResult(
            eval_loss=eval_loss,
            eval_tokens=tokens,
            eval_steps=eval_steps,
        )

    def health(self) -> TrainerHealth:
        state = self.get_full_state()
        return TrainerHealth(
            healthy=not self.nonfinite_detected,
            status="alive" if not self.nonfinite_detected else "failed",
            local_step=self.local_step,
            tokens_processed=self.tokens_processed,
            tokens_since_last_sync=self.tokens_since_last_sync,
            global_version=self.global_version,
            state_checksum=state.checksum,
            state_bytes_estimate=self.estimate_state_bytes(),
            num_parameters=self.num_parameters,
            final_loss=self.last_loss,
            final_eval_loss=self.last_eval_loss,
            nonfinite_detected=self.nonfinite_detected,
        )

    def mark_update_accepted(self) -> None:
        self.tokens_since_last_sync = 0
