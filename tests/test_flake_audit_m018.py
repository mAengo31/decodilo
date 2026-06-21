from decodilo.runtime.flake_audit import run_flake_audit


def test_flake_audit_uses_injected_runner_without_running_pytest() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str]) -> tuple[int, str, str]:
        calls.append(command)
        return 0, "passed", ""

    report = run_flake_audit(
        tests=["tests/test_local_process_failure.py"],
        repeat=3,
        command_runner=runner,
    )

    assert len(calls) == 3
    assert report.failures == []
    assert report.flaky_detected is False
