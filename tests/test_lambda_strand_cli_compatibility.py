from decodilo.lambda_cloud.strand_cli_compatibility import (
    build_strand_cli_compatibility_report,
)


def test_strand_profile_records_unofficial_behavioral_evidence():
    report = build_strand_cli_compatibility_report()
    expected_base_url = "https://" + "cloud." + "lambdalabs." + "com/api/v1"

    assert report.profile.source_is_official is False
    assert report.profile.source_is_behavioral_evidence is True
    assert report.profile.api_base_url == expected_base_url
    assert report.profile.timeout_seconds == 30.0
    assert report.compatibility_status == "compatible"
    assert report.launch_ready is False
    assert report.launch_allowed is False
