import pytest

from decodilo.errors import InvariantViolation
from decodilo.trainer.torch_optional import torch_available

pytestmark = pytest.mark.skipif(
    not torch_available(),
    reason="optional torch extra is not installed",
)


def _module_and_state():
    from decodilo.trainer.state import TrainerConfig
    from decodilo.trainer.torch_causal_lm import TinyTorchCausalLMTrainer
    from decodilo.trainer.torch_state import module_to_named_state

    trainer = TinyTorchCausalLMTrainer()
    trainer.initialize(
        run_id="state-codec",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=TrainerConfig(
            vector_dim=152,
            learning_rate=0.05,
            throughput_tokens_per_step=4,
            vocab_size=16,
            seq_len=4,
            batch_size=1,
            d_model=4,
            num_layers=0,
            num_heads=1,
            device="cpu",
        ),
    )
    return trainer.module, module_to_named_state(trainer.module, global_version=0)


def test_torch_state_strict_load_rejects_missing_extra_shape_and_checksum() -> None:
    from decodilo.trainer.torch_state import load_named_state_into_module

    module, state = _module_and_state()
    name = state.manifest.tensors[0].name

    missing = state.model_copy(
        update={"tensors": {k: v for k, v in state.tensors.items() if k != name}}
    )
    with pytest.raises(InvariantViolation, match="missing|checksum"):
        load_named_state_into_module(module, missing)

    extra = state.model_copy(update={"tensors": {**state.tensors, "extra.weight": [1.0]}})
    with pytest.raises(InvariantViolation, match="extra|checksum"):
        load_named_state_into_module(module, extra)

    bad_shape = state.model_copy(update={"tensors": {**state.tensors, name: [[0.0]]}})
    with pytest.raises(InvariantViolation, match="shape|checksum"):
        load_named_state_into_module(module, bad_shape)

    bad_checksum = state.model_copy(update={"checksum": "bad"})
    with pytest.raises(InvariantViolation, match="checksum"):
        load_named_state_into_module(module, bad_checksum)


def test_torch_state_export_rejects_nonfinite_tensor() -> None:
    from decodilo.trainer.torch_state import module_to_named_state

    module, _state = _module_and_state()
    first_param = next(module.parameters())
    first_param.data.view(-1)[0] = float("nan")

    with pytest.raises(InvariantViolation, match="non-finite"):
        module_to_named_state(module, global_version=0)
