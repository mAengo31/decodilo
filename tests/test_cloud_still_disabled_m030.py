from pathlib import Path


def test_m030_does_not_add_launch_now_or_execute_now_statuses():
    root = Path(__file__).resolve().parents[1]
    m030_files = [
        *root.glob("src/decodilo/lambda_cloud/second_attempt*.py"),
        root / "src/decodilo/lambda_cloud/response_loss_mitigation_review.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in m030_files)

    assert "launch_allowed=True" not in combined
    assert "launch_ready=True" not in combined
    assert "execute_now" not in combined
    assert "real_mutation_enabled=True" not in combined
