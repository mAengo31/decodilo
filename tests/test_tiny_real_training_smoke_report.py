from __future__ import annotations

from decodilo.dev.tiny_real_training_smoke import (
    load_tiny_real_training_smoke_report,
    run_tiny_real_training_smoke,
)


def test_tiny_real_training_smoke_report_is_bounded_and_honest(tmp_path):
    report_path = tmp_path / "tiny-real-training-smoke.json"
    report = run_tiny_real_training_smoke(
        synthetic=True,
        model="tiny-linear",
        steps=1,
        optimizer="adamw",
        out=report_path,
    )
    loaded = load_tiny_real_training_smoke_report(report_path)

    assert report.tiny_real_training_smoke_status == "passed"
    assert loaded.artifact_bytes == report_path.stat().st_size
    assert loaded.real_training_mechanics_exercised is True
    assert loaded.real_model_training_claimed is False
    assert loaded.paper_scale_training_claimed is False
    assert loaded.torch_required is False
    assert loaded.gpu_required is False
    assert loaded.background_process_started is False
    assert loaded.final_loss is not None
    assert loaded.initial_loss is not None
    assert loaded.final_loss < loaded.initial_loss
