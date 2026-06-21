from decodilo.lambda_cloud.strand_cli_gap_analysis import (
    StrandCLIGap,
    StrandCLIGapAnalysisReport,
    build_strand_cli_gap_analysis,
)
from decodilo.lambda_cloud.strand_cli_migration_plan import (
    build_strand_cli_migration_plan,
)


def test_no_gap_plan_allows_future_review_only():
    plan = build_strand_cli_migration_plan(build_strand_cli_gap_analysis())

    assert plan.migration_required is False
    assert plan.future_attempt_can_be_reviewed_after_migration is True
    assert plan.launch_ready is False
    assert plan.launch_allowed is False


def test_gap_plan_blocks_future_attempt_until_migration():
    analysis = StrandCLIGapAnalysisReport(
        gaps=[
            StrandCLIGap(
                area="launch_payload_shape",
                severity="blocker",
                expected="Strand launch payload",
                observed="old payload",
                migration_required=True,
            )
        ],
        migration_required=True,
        launch_blockers=["strand_gap:launch_payload_shape"],
    )

    plan = build_strand_cli_migration_plan(analysis)

    assert plan.migration_required is True
    assert plan.m034_attempt_should_remain_blocked is True
    assert "require existing SSH key name before future real launch" in (
        plan.required_launch_gate_changes
    )
