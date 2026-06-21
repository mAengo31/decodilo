from pathlib import Path

BANNED_IMPORTS = [
    "boto3",
    "google.cloud",
    "azure.storage",
    "azure-storage-blob",
    "s3fs",
]


def test_no_remote_sdk_dependencies_in_pyproject() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    for banned in BANNED_IMPORTS:
        assert banned not in pyproject


def test_no_remote_sdk_imports_or_cloud_env_reads_in_remote_modules() -> None:
    paths = [
        *Path("src/decodilo/storage").glob("remote_backend*.py"),
        *Path("src/decodilo/cloud").glob("remote_backend*.py"),
        *Path("src/decodilo/runtime").glob("remote_backend*.py"),
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        import_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            for banned in BANNED_IMPORTS:
                assert banned not in line, f"{path} imports {banned}"
        assert "os.environ" not in text
        assert ".getenv(" not in text
