from decodilo.lambda_cloud.m036r_report import build_lambda_m036r_report
from decodilo.lambda_cloud.strand_cli_compatibility import (
    build_strand_cli_compatibility_report,
)
from decodilo.lambda_cloud.strand_cli_gap_analysis import build_strand_cli_gap_analysis
from decodilo.lambda_cloud.strand_cli_migration_plan import (
    build_strand_cli_migration_plan,
)


def test_m036r_report_cannot_enable_launch():
    compatibility = build_strand_cli_compatibility_report()
    gaps = build_strand_cli_gap_analysis()
    plan = build_strand_cli_migration_plan(gaps)
    report = build_lambda_m036r_report(
        compatibility=compatibility,
        gap_analysis=gaps,
        migration_plan=plan,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
