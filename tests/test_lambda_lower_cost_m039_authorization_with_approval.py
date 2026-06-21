from lambda_m038_helpers import authorization


def test_m039_authorization_passes_with_complete_future_approval_only():
    report = authorization(approval_complete=True)

    assert report.authorization_status == "authorized_for_future_m039_lower_cost_launch_attempt"
    assert report.launch_authorized_for_next_milestone is True
    assert report.launch_authorized_now is False
    assert report.estimated_30min_cost == 1.645
    assert report.buffered_estimated_30min_cost == 1.89175
    assert report.selected_ssh_key_hash is not None
    assert report.selected_ssh_key_hash.startswith("sha256:")
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.real_mutation_enabled is False
