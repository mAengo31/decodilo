import json

import pytest

from decodilo.lambda_cloud import secret_file as secret_file_module
from decodilo.lambda_cloud.credential_model import LambdaCredentialError
from decodilo.lambda_cloud.secret_file import (
    load_lambda_api_key_from_env_file,
    load_lambda_api_key_from_file,
)


def test_lambda_secret_file_loads_and_redacts(tmp_path) -> None:
    secret = "fixture-readonly-key-123"
    path = tmp_path / "lambda_key.txt"
    path.write_text(secret, encoding="utf-8")
    path.chmod(0o600)

    loaded, report = load_lambda_api_key_from_file(path)

    assert loaded == secret
    payload = report.to_json()
    assert secret not in payload
    assert report.key_sha256_prefix
    assert json.loads(payload)["redacted"] is True


def test_lambda_secret_file_rejects_missing_empty_and_oversized(tmp_path) -> None:
    with pytest.raises(LambdaCredentialError):
        load_lambda_api_key_from_file(tmp_path / "missing")

    empty = tmp_path / "empty"
    empty.write_text("", encoding="utf-8")
    empty.chmod(0o600)
    with pytest.raises(LambdaCredentialError):
        load_lambda_api_key_from_file(empty)

    large = tmp_path / "large"
    large.write_text("x" * 5000, encoding="utf-8")
    large.chmod(0o600)
    with pytest.raises(LambdaCredentialError):
        load_lambda_api_key_from_file(large)


def test_lambda_secret_file_rejects_multiline_and_world_readable(tmp_path) -> None:
    multiline = tmp_path / "multi"
    multiline.write_text("one\ntwo\n", encoding="utf-8")
    multiline.chmod(0o600)
    with pytest.raises(LambdaCredentialError):
        load_lambda_api_key_from_file(multiline)

    world = tmp_path / "world"
    world.write_text("fixture-readonly-key", encoding="utf-8")
    world.chmod(0o604)
    with pytest.raises(LambdaCredentialError):
        load_lambda_api_key_from_file(world)


def test_lambda_env_file_loads_only_when_explicit_and_redacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAMBDA_API_KEY", "lambda_os_env_value_should_not_be_used")
    env_file = tmp_path / ".env"
    secret = "lambda_file_value_123456789"
    env_file.write_text(f'LAMBDA_API_KEY="{secret}"\nOTHER=value\n', encoding="utf-8")

    loaded, report = load_lambda_api_key_from_env_file(
        env_file,
        env_key="LAMBDA_API_KEY",
    )

    assert loaded == secret
    payload = report.to_json()
    assert secret not in payload
    assert "lambda_os_env_value_should_not_be_used" not in payload
    assert report.secret_source == "env_file"
    assert report.env_file_basename == ".env"
    assert report.env_key == "LAMBDA_API_KEY"
    assert json.loads(payload)["redacted"] is True


def test_lambda_env_file_rejects_missing_key_empty_and_huge_values(tmp_path) -> None:
    with pytest.raises(LambdaCredentialError, match="missing"):
        load_lambda_api_key_from_env_file(tmp_path / ".env")

    env_file = tmp_path / ".env"
    env_file.write_text("OTHER=value\n", encoding="utf-8")
    with pytest.raises(LambdaCredentialError, match="did not contain LAMBDA_API_KEY"):
        load_lambda_api_key_from_env_file(env_file)

    env_file.write_text("LAMBDA_API_KEY=\n", encoding="utf-8")
    with pytest.raises(LambdaCredentialError, match="empty"):
        load_lambda_api_key_from_env_file(env_file)

    env_file.write_text("LAMBDA_API_KEY=" + ("x" * 5000), encoding="utf-8")
    with pytest.raises(LambdaCredentialError, match="too large"):
        load_lambda_api_key_from_env_file(env_file)


def test_lambda_env_file_reports_tracked_warning_without_secret(tmp_path, monkeypatch) -> None:
    secret = "lambda_tracked_value_123456789"
    env_file = tmp_path / ".env"
    env_file.write_text(f"LAMBDA_API_KEY={secret}\n", encoding="utf-8")
    monkeypatch.setattr(
        secret_file_module,
        "_git_secret_file_status",
        lambda path: ("tracked", False),
    )

    loaded, report = load_lambda_api_key_from_env_file(env_file)

    assert loaded == secret
    assert any("HIGH-SEVERITY" in warning for warning in report.warnings)
    assert secret not in report.to_json()
