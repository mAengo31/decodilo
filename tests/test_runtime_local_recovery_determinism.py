from __future__ import annotations

from pathlib import Path

from decodilo.runtime.ci_profile_manifest import classify_test_file


def test_local_recovery_test_has_explicit_runtime_profile_markers() -> None:
    source = Path("tests/test_local_process_failure.py").read_text(encoding="utf-8")

    assert "pytest.mark.runtime_local" in source
    assert "pytest.mark.subprocess_heavy" in source
    markers = classify_test_file("tests/test_local_process_failure.py")
    assert "runtime_local" in markers
    assert "subprocess_heavy" in markers
    assert "quick" not in markers


def test_local_recovery_assertion_uses_post_recovery_event_sequence() -> None:
    source = Path("tests/test_local_process_failure.py").read_text(encoding="utf-8")

    assert source.count('"learner-0:after-round=2"') >= 2
    assert '"learner-0:after-round=4"' not in source
    assert 'event["sequence"] > recovered[0]["sequence"]' in source
    assert "post-recovery commit" in source
