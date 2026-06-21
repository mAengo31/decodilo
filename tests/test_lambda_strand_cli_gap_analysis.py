from decodilo.lambda_cloud.strand_cli_gap_analysis import build_strand_cli_gap_analysis
from decodilo.lambda_cloud.strand_cli_request_shapes import validate_strand_launch_payload


def test_current_surface_matches_strand_after_migration():
    report = build_strand_cli_gap_analysis()

    assert report.migration_required is False
    assert report.launch_blockers == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_old_payload_names_are_blockers_in_fixture():
    try:
        validate_strand_launch_payload(
            {
                "region": "us-west-1",
                "instance_type": "gpu_1x_h100_pcie",
                "quantity": 1,
            }
        )
    except Exception as exc:  # noqa: BLE001
        assert type(exc).__name__ == "ValidationError"
    else:  # pragma: no cover
        raise AssertionError("old payload shape should fail")
