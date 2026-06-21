from pathlib import Path


def test_fake_lifecycle_modules_do_not_import_real_network_clients() -> None:
    root = Path("src/decodilo/lambda_cloud")
    fake_files = [
        path
        for path in sorted(root.glob("fake_*.py"))
        if path.name not in {"fake_transport.py", "fake_server.py"}
    ]
    forbidden = ["urllib.request", "http.client", "requests", "httpx", "aiohttp"]

    offenders: list[str] = []
    for path in fake_files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path}:{token}")

    assert offenders == []


def test_fake_lifecycle_cli_has_no_live_secret_options() -> None:
    text = Path("src/decodilo/cli.py").read_text(encoding="utf-8")
    fake_section = text.split(
        'lambda_fake_lifecycle = lambda_sub.add_parser("fake-lifecycle")',
        1,
    )[1]
    fake_section = fake_section.split(
        'lambda_readiness = lambda_sub.add_parser("readiness-summary")',
        1,
    )[0]

    assert "--api-key" not in fake_section
    assert "--api-key-file" not in fake_section
    assert "--env-file" not in fake_section
    assert "--live" not in fake_section
