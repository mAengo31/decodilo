from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger


def test_real_launch_ledger_owned_only():
    ledger = LambdaM029LaunchLedger(run_id="run").record_owned(
        "fake-i-owned",
        launch_attempt_id="launch-key",
    )

    assert ledger.can_terminate("fake-i-owned") is True
    assert ledger.can_terminate("fake-i-other") is False

    terminated = ledger.record_terminated(terminate_attempt_id="term-key", verified=True)

    assert terminated.termination_verified is True
    assert terminated.resource_state == "terminated"
