from __future__ import annotations

from pathlib import Path

from decodilo.runtime.ci_profile_manifest import classify_test_file
from decodilo.runtime.ci_profile_report import build_ci_profile_report


def test_tests_do_not_embed_direct_lambda_api_url() -> None:
    offenders: list[str] = []
    live_url = "https://" + "cloud.lambdalabs.com"
    for path in Path("tests").glob("test_*.py"):
        if live_url in path.read_text(encoding="utf-8"):
            offenders.append(str(path))

    assert offenders == []


def test_tests_do_not_import_dot_env_helpers_or_project_env_file() -> None:
    offenders: list[str] = []
    forbidden_snippets = (
        "load_" + "dotenv",
        "from " + "dotenv",
        "import " + "dotenv",
        "Path(" + '".env"' + ")",
    )
    for path in Path("tests").glob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        if any(snippet in text for snippet in forbidden_snippets):
            offenders.append(str(path))

    assert offenders == []


def test_real_mutation_profile_is_never_quick() -> None:
    markers = classify_test_file("tests/test_lambda_real_mutation_preflight.py")

    assert "lambda_real_mutation" not in markers
    assert "quick" not in markers


def test_quick_profile_does_not_include_env_or_operator_key_tests() -> None:
    report = build_ci_profile_report()
    quick_nodeids = "\n".join(report.tests_by_profile["quick"])

    assert ".env" not in quick_nodeids
    assert "requires_operator_key" not in quick_nodeids
    assert "secret_file" not in quick_nodeids
