from pathlib import Path


def test_no_real_lambda_post_put_patch_delete_transport_m022() -> None:
    text = Path("src/decodilo/lambda_cloud/real_read_only_transport.py").read_text(
        encoding="utf-8"
    )

    assert '"POST"' not in text
    assert '"PUT"' not in text
    assert '"PATCH"' not in text
    assert '"DELETE"' not in text


def test_fake_mutation_modules_do_not_import_live_transport() -> None:
    offenders = []
    for path in Path("src/decodilo/lambda_cloud").glob("fake_mutation*.py"):
        text = path.read_text(encoding="utf-8")
        if "real_read_only_transport" in text or "LiveReadOnlyLambdaCloudClient" in text:
            offenders.append(str(path))

    assert offenders == []
