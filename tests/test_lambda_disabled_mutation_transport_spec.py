from pydantic import ValidationError

from decodilo.lambda_cloud.disabled_mutation_transport_spec import (
    LambdaDisabledMutationTransportSpec,
    build_lambda_disabled_mutation_transport_spec,
)


def test_disabled_mutation_transport_spec_is_non_executable() -> None:
    spec = build_lambda_disabled_mutation_transport_spec()

    assert spec.disabled_in_current_build is True
    assert spec.no_code_implemented is True
    assert spec.executable_transport_available is False
    assert spec.launch_allowed is False


def test_disabled_mutation_transport_spec_rejects_executable_state() -> None:
    try:
        LambdaDisabledMutationTransportSpec(executable_transport_available=True)
    except ValidationError as exc:
        assert "cannot be executable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("executable mutation transport spec accepted")


def test_disabled_mutation_transport_spec_serializes() -> None:
    assert "M023 is review-only" in build_lambda_disabled_mutation_transport_spec().to_json()
