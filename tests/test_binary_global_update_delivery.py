import pytest
from m010_binary_helpers import run_binary_local

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_binary_global_update_delivery_ack_happens_after_successful_apply(tmp_path) -> None:
    report = run_binary_local(tmp_path)

    assert report["metrics"]["binary_global_update_messages_sent"] > 0
    assert report["metrics"]["binary_global_update_apply_failures"] == 0
    assert report["metrics"]["global_update_acks"] > 0
    assert (
        report["metrics"]["global_update_acks"]
        <= report["metrics"]["global_update_messages_sent"]
    )
    assert all(lag >= 0 for lag in report["metrics"]["learner_update_lag_current"].values())
