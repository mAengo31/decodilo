from lambda_m040_helpers import authorization, write_m040_inputs

from decodilo.lambda_cloud.availability_first_authorization_package import (
    build_lambda_availability_first_authorization_package,
)


def test_complete_availability_first_package_authorizes_future_review(tmp_path):
    report = authorization(tmp_path)

    assert (
        report.authorization_status
        == "authorized_for_future_availability_first_launch_review"
    )
    assert report.operator_risk_acceptance_required is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_capacity_closeout_blocks_authorization(tmp_path):
    paths = write_m040_inputs(tmp_path)
    paths["closeout"].unlink()

    try:
        build_lambda_availability_first_authorization_package(
            capacity_closeout=paths["closeout"],
            capacity_policy=paths["policy"],
            rank=paths["rank"],
            plan=paths["plan"],
            ssh_key_selection=paths["ssh"],
            response_loss_controls=paths["controls"],
        )
    except FileNotFoundError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("missing capacity closeout should fail")


def test_no_candidate_blocks_authorization(tmp_path):
    paths = write_m040_inputs(tmp_path)
    paths["rank"].write_text(
        paths["rank"].read_text(encoding="utf-8").replace(
            "selected_catalog_only_requires_risk_acceptance",
            "no_candidate",
        ),
        encoding="utf-8",
    )
    # The edited fixture still contains selected_candidate, so remove it structurally.
    import json

    data = json.loads(paths["rank"].read_text(encoding="utf-8"))
    data["selected_candidate"] = None
    data["blockers"] = ["no_viable_availability_first_candidate"]
    paths["rank"].write_text(json.dumps(data), encoding="utf-8")

    report = build_lambda_availability_first_authorization_package(
        capacity_closeout=paths["closeout"],
        capacity_policy=paths["policy"],
        rank=paths["rank"],
        plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )

    assert report.authorization_status == "not_authorized"
    assert "no_viable_availability_first_candidate" in report.blockers
