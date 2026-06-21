from __future__ import annotations

from lambda_m051_helpers import m051_discovery, run_m051_fake

from decodilo.lambda_cloud.live_discovery_report import write_lambda_live_discovery_report
from decodilo.lambda_cloud.m051_bootstrap_evidence_package import (
    build_lambda_m051_bootstrap_evidence_package_from_paths,
)


def test_m051_bootstrap_evidence_package_summarizes_metadata_only_run(tmp_path):
    result = run_m051_fake(tmp_path)
    post_discovery = tmp_path / "post-discovery.json"
    write_lambda_live_discovery_report(
        post_discovery,
        m051_discovery(include_candidate=True).model_copy(update={"instance_types": []}),
    )

    package = build_lambda_m051_bootstrap_evidence_package_from_paths(
        workdir=result.workdir,  # type: ignore[attr-defined]
        evidence_schema=result.paths["evidence_schema"],  # type: ignore[attr-defined]
        post_discovery=post_discovery,
    )

    assert package.evidence_complete is True
    assert package.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert package.ssh_attempted is False
    assert package.remote_command_attempted is False
    assert package.package_install_attempted is False
    assert package.training_attempted is False
    assert package.termination_verified is True
    assert package.final_instance_count == 0
    assert package.final_unmanaged_count == 0
