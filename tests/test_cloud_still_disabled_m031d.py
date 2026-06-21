from pathlib import Path


def test_m031d_does_not_enable_launch_or_mutation():
    root = Path(__file__).resolve().parents[1]
    m031d_files = [
        *root.glob("src/decodilo/lambda_cloud/m031_*.py"),
        root / "src/decodilo/lambda_cloud/repeated_response_loss_review.py",
        root / "src/decodilo/lambda_cloud/launch_response_loss_root_cause.py",
        root / "src/decodilo/lambda_cloud/launch_transport_diagnostics.py",
        root / "src/decodilo/lambda_cloud/launch_endpoint_diagnostics.py",
        root / "src/decodilo/lambda_cloud/launch_response_capture_policy.py",
        root / "src/decodilo/lambda_cloud/future_launch_hold.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in m031d_files)

    assert "launch_allowed=True" not in combined
    assert "launch_ready=True" not in combined
    assert "real_mutation_enabled=True" not in combined
    assert "execute_now" not in combined
