from decodilo.lambda_cloud.secret_handling_review import review_lambda_secret_handling


def test_secret_handling_review_clean_evidence_passes(tmp_path):
    clean = tmp_path / "clean.json"
    clean.write_text('{"secret_redacted": true}\n', encoding="utf-8")

    review = review_lambda_secret_handling([clean])

    assert review.secret_handling_passed is True
    assert review.launch_allowed is False


def test_secret_handling_review_detects_injected_secret(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"Authorization": "Bearer lambda_abcdefghijklmnop"}\n', encoding="utf-8")

    review = review_lambda_secret_handling([bad])

    assert review.secret_handling_passed is False
    assert review.secret_like_findings == [str(bad)]
