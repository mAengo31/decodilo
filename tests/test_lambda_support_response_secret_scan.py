from decodilo.lambda_cloud.support_response_secret_scan import (
    scan_lambda_support_response_text,
)


def test_support_response_secret_scan_passes_clean_text():
    report = scan_lambda_support_response_text('{"answer": "POST /instances"}')

    assert report.scan_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_support_response_secret_scan_blocks_secret_like_values():
    report = scan_lambda_support_response_text("Authorization: Bearer abc123")

    assert report.scan_passed is False
    assert "authorization_header" in report.findings
    assert report.blockers

