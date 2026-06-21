from decodilo.lambda_cloud.m029_discovery_diff import build_lambda_m029_discovery_diff
from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger


def test_no_pre_post_instances_high_no_instance_created():
    report = build_lambda_m029_discovery_diff(
        pre_discovery={"instances": []},
        post_discovery={"instances": []},
        ledger=LambdaM029LaunchLedger(run_id="run"),
    )

    assert report.confidence == "high_no_instance_created"
    assert report.possible_owned_candidates == []


def test_post_instance_creates_candidate():
    report = build_lambda_m029_discovery_diff(
        pre_discovery={"instances": []},
        post_discovery={
            "instances": [
                {"instance_id": "fake-i-1", "status": "running", "instance_type": "gpu"}
            ]
        },
        ledger=LambdaM029LaunchLedger(run_id="run"),
    )

    assert report.confidence == "possible_instance_created"
    assert len(report.possible_owned_candidates) == 1


def test_disappeared_instance_uncertain():
    report = build_lambda_m029_discovery_diff(
        pre_discovery={"instances": [{"instance_id": "fake-i-old", "status": "running"}]},
        post_discovery={"instances": []},
        ledger=LambdaM029LaunchLedger(run_id="run"),
    )

    assert report.confidence == "uncertain"


def test_unmanaged_billable_instance_requires_review():
    report = build_lambda_m029_discovery_diff(
        pre_discovery={"instances": [{"instance_id": "fake-i-other", "status": "running"}]},
        post_discovery={"instances": [{"instance_id": "fake-i-other", "status": "running"}]},
        ledger=LambdaM029LaunchLedger(run_id="run"),
    )

    assert report.unmanaged_instances
