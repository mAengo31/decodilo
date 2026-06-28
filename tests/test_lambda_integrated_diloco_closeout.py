from __future__ import annotations

from lambda_m086_helpers import make_m085r_workdir, write_m086_integrated_closeout_chain

from decodilo.lambda_cloud.integrated_diloco_closeout import (
    load_lambda_integrated_diloco_closeout,
)


def test_integrated_diloco_closeout_succeeds(tmp_path):
    paths = write_m086_integrated_closeout_chain(
        tmp_path,
        make_m085r_workdir(tmp_path),
    )

    closeout = load_lambda_integrated_diloco_closeout(paths["closeout"])

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.integrated_diloco_success is True
    assert closeout.parameter_fragment_semantics == "not_exercised"
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
