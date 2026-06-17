from pathlib import Path


def test_learner_worker_uses_trainer_adapter_not_fake_learner() -> None:
    source = Path("src/decodilo/runtime/learner_worker.py").read_text(encoding="utf-8")

    assert "create_trainer" in source
    assert "FakeLearner" not in source


def test_runtime_does_not_import_fake_model_helpers() -> None:
    runtime_sources = [
        Path("src/decodilo/runtime/learner_worker.py").read_text(encoding="utf-8"),
        Path("src/decodilo/runtime/syncer_service.py").read_text(encoding="utf-8"),
    ]

    assert all("decodilo.sim.fake_model" not in source for source in runtime_sources)
