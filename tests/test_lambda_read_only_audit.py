from decodilo.lambda_cloud.read_only_audit import (
    LambdaReadOnlyAuditEntry,
    audit_lambda_read_only,
)


def test_lambda_read_only_audit_passes_clean_entries() -> None:
    report = audit_lambda_read_only(
        [
            LambdaReadOnlyAuditEntry(
                operation="list_instances",
                method="GET",
                endpoint="/instances",
                allowed=True,
                status_code=200,
                live_api_used=True,
            )
        ]
    )

    assert report.passed
    assert report.read_operations == 1
    assert report.mutating_operations == 0


def test_lambda_read_only_audit_fails_mutation_and_secret() -> None:
    report = audit_lambda_read_only(
        [
            LambdaReadOnlyAuditEntry(
                operation="launch_instance",
                method="POST",
                endpoint="/instances",
                allowed=True,
                status_code=200,
                live_api_used=True,
                mutation=True,
            ),
            LambdaReadOnlyAuditEntry(
                operation="list_instances",
                method="GET",
                endpoint="Bearer lambda_12345678901234567890",
                allowed=True,
                status_code=200,
                live_api_used=True,
            ),
        ]
    )

    assert not report.passed
    assert report.mutating_operations == 1
    assert report.errors
