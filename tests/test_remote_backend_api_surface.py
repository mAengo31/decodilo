from decodilo.storage.remote_backend_api_surface import default_remote_backend_api_surface


def test_api_surface_lists_required_future_operations_but_implements_none() -> None:
    surface = default_remote_backend_api_surface()
    operation_ids = {operation.operation_id for operation in surface.operations}

    assert "put_artifact" in operation_ids
    assert "conditional_put_manifest" in operation_ids
    assert all(operation.current_milestone_implemented is False for operation in surface.operations)
    assert surface.remote_backend_enabled is False
    assert surface.model_validate_json(surface.to_json()) == surface
