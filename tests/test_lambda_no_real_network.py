import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {"requests", "httpx", "aiohttp", "socket"}


def test_lambda_cloud_modules_have_no_real_network_imports() -> None:
    for path in Path("src/decodilo/lambda_cloud").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                assert names.isdisjoint(FORBIDDEN_IMPORTS), path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS, path


def test_lambda_cli_has_no_api_key_flag() -> None:
    cli_source = Path("src/decodilo/cli.py").read_text(encoding="utf-8")

    assert '"--api-key"' not in cli_source
    assert "'--api-key'" not in cli_source
    assert "--api-key-file" in cli_source
    assert "--allow-mutation" not in cli_source
