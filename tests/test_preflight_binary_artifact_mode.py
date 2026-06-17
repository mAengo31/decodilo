import pytest
from m010_binary_helpers import run_binary_local

from decodilo.runtime.preflight import run_local_preflight

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_local_preflight_passes_binary_v1_local_run(tmp_path) -> None:
    run_binary_local(tmp_path)

    result = run_local_preflight(workdir=tmp_path)

    assert result.preflight_passed is True
    assert result.launch_ready is False
    assert result.launch_allowed is False
    assert result.resource_limit_summary["tensor_artifact_codec"] == "binary_v1"
    assert result.resource_limit_summary["remote_backend_enabled"] is False
    assert (
        result.resource_limit_summary["artifact_backend_contract"]["range_reads_supported"]
        is True
    )
    assert result.resource_limit_summary["out_of_core_merge_configured"] is True
