from pathlib import Path


def test_tests_do_not_call_real_lambda_url() -> None:
    live_host = "https://" + "cloud.lambdalabs.com"
    for path in Path("tests").glob("test_lambda_*.py"):
        source = path.read_text(encoding="utf-8")
        assert live_host not in source, path


def test_lambda_modules_do_not_read_lambda_env_vars() -> None:
    for path in Path("src/decodilo/lambda_cloud").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "os.environ" not in source
        assert "getenv(" not in source
        assert "AWS_" not in source
