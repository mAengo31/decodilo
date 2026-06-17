from decodilo.trainer.contract_tests import assert_basic_trainer_contract
from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.registry import create_trainer


def test_numpy_convex_satisfies_basic_trainer_contract() -> None:
    assert_basic_trainer_contract(NumpyConvexTrainer())


def test_trainer_registry_creates_known_adapters() -> None:
    assert create_trainer("numpy_convex").__class__.__name__ == "NumpyConvexTrainer"
    assert create_trainer("scripted").__class__.__name__ == "ScriptedTrainer"
