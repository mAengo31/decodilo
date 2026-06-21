from lambda_m037_helpers import reauth_package, shape_selection

from decodilo.lambda_cloud.lower_cost_reauthorization_package import (
    build_lambda_lower_cost_reauthorization_package,
)


def test_lower_cost_selected_requires_future_reauthorization():
    package = reauth_package()

    assert package.package_status == "reauthorization_required"
    assert package.selected_shape == "gpu_1x_h100_pcie"
    assert package.required_regeneration_steps
    assert package.launch_ready is False
    assert package.launch_allowed is False


def test_keep_current_shape_does_not_require_reauthorization():
    selection = shape_selection().model_copy(
        update={"selection_status": "keep_current_shape", "selected_shape": "gpu_8x_h100_sxm"}
    )
    package = build_lambda_lower_cost_reauthorization_package(selection=selection)

    assert package.package_status == "not_required"

