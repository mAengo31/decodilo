import os

from pydantic import ValidationError

from decodilo.lambda_cloud.real_mutation_feature_flags import (
    LambdaMutationFeatureFlags,
    default_lambda_mutation_feature_flags,
    evaluate_lambda_mutation_feature_flags,
)


def test_feature_flags_default_disabled() -> None:
    flags = default_lambda_mutation_feature_flags()
    report = evaluate_lambda_mutation_feature_flags(flags)

    assert flags.real_mutation_feature_present is True
    assert flags.real_mutation_transport_executable is False
    assert flags.launch_execution_enabled is False
    assert report.launch_allowed is False


def test_launch_execution_enabled_rejected() -> None:
    try:
        LambdaMutationFeatureFlags(launch_execution_enabled=True)
    except ValidationError as exc:
        assert "cannot enable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("launch execution flag accepted")


def test_mutation_arming_allowed_rejected() -> None:
    try:
        LambdaMutationFeatureFlags(mutation_arming_allowed=True)
    except ValidationError as exc:
        assert "cannot enable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("arming flag accepted")


def test_environment_variables_cannot_enable(monkeypatch) -> None:
    monkeypatch.setenv("DECODILO_LAMBDA_ENABLE_MUTATION", "1")

    flags = default_lambda_mutation_feature_flags()

    assert os.environ["DECODILO_LAMBDA_ENABLE_MUTATION"] == "1"
    assert flags.launch_execution_enabled is False
    assert flags.mutation_arming_allowed is False
