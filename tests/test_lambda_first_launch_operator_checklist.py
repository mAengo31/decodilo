from decodilo.lambda_cloud.first_launch_operator_checklist import (
    build_lambda_first_launch_operator_checklist,
    evaluate_lambda_first_launch_operator_checklist,
)


def test_operator_checklist_incomplete_by_default():
    checklist = build_lambda_first_launch_operator_checklist()
    report = evaluate_lambda_first_launch_operator_checklist(checklist)

    assert report.checklist_complete_for_review is False
    assert report.blockers
    assert report.launch_allowed is False


def test_operator_checklist_complete_for_review_only():
    checklist = build_lambda_first_launch_operator_checklist(acknowledge_all=True)
    report = evaluate_lambda_first_launch_operator_checklist(checklist)

    assert report.checklist_complete_for_review is True
    assert checklist.review_only_complete is True
    assert checklist.launch_ready is False
