from decodilo.lambda_cloud.m034_discovery_diff import build_lambda_m034_discovery_diff


def test_zero_pre_post_closeout_instances_high_no_created():
    report = build_lambda_m034_discovery_diff(
        pre_discovery={"instances": []},
        post_discovery={"instances": []},
        closeout_discovery={"instances": []},
    )

    assert report.confidence == "high_no_instance_created"
    assert report.possible_owned_candidates == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_visible_post_instance_is_candidate():
    report = build_lambda_m034_discovery_diff(
        pre_discovery={"instances": []},
        post_discovery={
            "instances": [
                {"id": "fake-i-1", "status": "running", "instance_type": "gpu_8x"}
            ]
        },
    )

    assert report.confidence == "possible_instance_created"
    assert len(report.possible_owned_candidates) == 1


def test_disappeared_instance_uncertain():
    report = build_lambda_m034_discovery_diff(
        pre_discovery={"instances": [{"id": "fake-i-old", "status": "running"}]},
        post_discovery={"instances": []},
    )

    assert report.confidence == "uncertain"
