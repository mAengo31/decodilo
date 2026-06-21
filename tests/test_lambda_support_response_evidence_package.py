from lambda_m037_helpers import complete_support_paths, support_package

from decodilo.lambda_cloud.support_response_evidence_package import (
    build_lambda_support_response_evidence_package,
)


def test_support_response_evidence_package_builds_from_complete_fixture(tmp_path):
    package = support_package(tmp_path)

    assert package.package_passed is True
    assert package.support_response.present is True
    assert package.secret_scan.scan_passed is True
    assert package.launch_ready is False
    assert package.launch_allowed is False


def test_missing_support_response_blocks_package(tmp_path):
    paths = complete_support_paths(tmp_path)
    package = build_lambda_support_response_evidence_package(
        support_request=paths["support_request"],
    )

    assert package.package_passed is False
    assert "support_response_missing" in package.blockers


def test_secret_like_support_response_blocks_package(tmp_path):
    paths = complete_support_paths(tmp_path)
    paths["support_response"].write_text("Bearer abc123", encoding="utf-8")

    package = build_lambda_support_response_evidence_package(
        support_request=paths["support_request"],
        support_response=paths["support_response"],
    )

    assert package.package_passed is False
    assert any("secret_like_value_detected" in item for item in package.blockers)


def test_hash_mismatch_blocks_package(tmp_path):
    paths = complete_support_paths(tmp_path)
    package = build_lambda_support_response_evidence_package(
        support_request=paths["support_request"],
        support_response=paths["support_response"],
        expected_hashes={"support_response": "not-a-real-hash"},
    )

    assert "support_response_hash_mismatch" in package.blockers

