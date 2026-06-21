from lambda_m034d_helpers import write_m034c_sent_journal

from decodilo.lambda_cloud.launch_failure_journal_recovery import (
    recover_lambda_launch_failure_from_journal,
)


def test_missing_report_with_sent_launch_recovers_from_journal(tmp_path):
    journal = write_m034c_sent_journal(tmp_path)

    report = recover_lambda_launch_failure_from_journal(
        journal,
        report_path=tmp_path / "missing-report.json",
    )

    assert report.launch_request_sent is True
    assert report.response_received is False
    assert report.missing_report_detected is True
    assert report.recovered_from_journal is True
    assert report.manual_review_required is True
    assert "missing_m029_report_after_launch_request" in report.blockers


def test_corrupted_journal_fails_clearly(tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text("{not-json}\n", encoding="utf-8")

    report = recover_lambda_launch_failure_from_journal(journal)

    assert report.recovered_from_journal is False
    assert report.corrupted is True
    assert "launch_journal_corrupted" in report.blockers
