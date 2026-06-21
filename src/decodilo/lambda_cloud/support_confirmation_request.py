"""M036 structured support/operator confirmation request."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaSupportQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    category: str
    question: str
    required: bool = True


class LambdaSupportConfirmationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = "lambda-m036-support-confirmation-request"
    provider: str = "lambda"
    questions: list[LambdaSupportQuestion]
    no_secrets_included: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSupportConfirmationRequest:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("support confirmation request cannot enable launch")
        if not self.no_secrets_included:
            raise ValueError("support confirmation request must not include secrets")
        return self


class LambdaSupportConfirmationRequestReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    support_request: LambdaSupportConfirmationRequest
    required_question_count: int
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSupportConfirmationRequestReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M036 support request cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_support_confirmation_request() -> LambdaSupportConfirmationRequestReport:
    questions = [
        ("launch_method", "launch_endpoint", "What is the correct launch HTTP method?"),
        (
            "launch_path_template",
            "launch_endpoint",
            "What is the correct launch endpoint path template?",
        ),
        (
            "launch_required_fields",
            "launch_endpoint",
            "What request fields are required to launch one instance?",
        ),
        (
            "launch_optional_fields",
            "launch_endpoint",
            "What request fields are optional for launch?",
        ),
        (
            "launch_omit_user_data",
            "launch_endpoint",
            "Do user-data, cloud-init, or setup-script fields exist, and how are they omitted?",
        ),
        (
            "launch_idempotency",
            "launch_endpoint",
            "Does launch support an idempotency key or client token?",
        ),
        (
            "launch_success_status",
            "launch_endpoint",
            "What success HTTP status code should launch return?",
        ),
        (
            "launch_content_type",
            "response_shape",
            "What response content type should launch return?",
        ),
        (
            "launch_response_shape",
            "response_shape",
            "What is the expected launch response body shape?",
        ),
        (
            "launch_instance_id_field",
            "response_shape",
            "Which exact response field contains the launched instance ID?",
        ),
        (
            "launch_async_without_id",
            "response_shape",
            "Can launch return accepted/async success without an instance ID?",
        ),
        (
            "launch_timeout_may_create",
            "ambiguous_response",
            "Can launch time out while still creating an instance?",
        ),
        (
            "ambiguous_launch_reconciliation",
            "ambiguous_response",
            "How should ambiguous launch responses be reconciled?",
        ),
        (
            "terminate_method",
            "terminate_endpoint",
            "What is the correct terminate HTTP method?",
        ),
        (
            "terminate_path_template",
            "terminate_endpoint",
            "What is the correct terminate endpoint path template?",
        ),
        (
            "terminate_required_fields",
            "terminate_endpoint",
            "What request fields are required to terminate an owned instance?",
        ),
        (
            "terminate_success_status",
            "terminate_endpoint",
            "What success HTTP status code should terminate return?",
        ),
        (
            "terminate_response_shape",
            "response_shape",
            "What is the expected terminate response body shape?",
        ),
        (
            "termination_terminal_states",
            "terminate_endpoint",
            "What terminal states indicate successful termination?",
        ),
        (
            "terminate_timeout_may_terminate",
            "ambiguous_response",
            "Can terminate time out while still terminating the instance?",
        ),
        (
            "termination_verification",
            "terminate_endpoint",
            "How should termination be verified through read-only endpoints?",
        ),
        (
            "list_instances_endpoint",
            "listing_discovery",
            "What endpoint lists running instances?",
        ),
        ("list_pagination", "listing_discovery", "Is instance listing paginated?"),
        ("list_region_scope", "listing_discovery", "Is instance listing region-scoped?"),
        (
            "list_consistency",
            "listing_discovery",
            "Can instance listing be delayed or eventually consistent?",
        ),
        (
            "instance_type_listing",
            "listing_discovery",
            "Is instance-type listing account-specific or unsupported?",
        ),
        ("quota_endpoint", "quota_usage", "Does a quota endpoint exist for this account/API?"),
        ("usage_endpoint", "quota_usage", "Does a usage/billing endpoint exist?"),
        ("launch_rate_limits", "rate_limits", "What rate limits apply to launch?"),
        ("terminate_rate_limits", "rate_limits", "What rate limits apply to terminate?"),
        ("read_rate_limits", "rate_limits", "What rate limits apply to read/list calls?"),
        (
            "safe_lifecycle_shape",
            "first_launch_safety",
            "What is the safest lowest-cost shape for launch/terminate smoke?",
        ),
        (
            "h100_pcie_1x_supported",
            "first_launch_safety",
            "Is 1x H100 PCIe supported in the target account and region?",
        ),
        (
            "lower_cost_non_h100_shape",
            "first_launch_safety",
            "Is a lower-cost non-H100 shape available for lifecycle smoke?",
        ),
    ]
    request = LambdaSupportConfirmationRequest(
        questions=[
            LambdaSupportQuestion(
                question_id=question_id,
                category=category,
                question=question,
            )
            for question_id, category, question in questions
        ],
    )
    return LambdaSupportConfirmationRequestReport(
        support_request=request,
        required_question_count=len([item for item in request.questions if item.required]),
        warnings=["M036 support confirmation request performs no API calls"],
    )


def load_lambda_support_confirmation_request_report(
    path: str | Path,
) -> LambdaSupportConfirmationRequestReport:
    return LambdaSupportConfirmationRequestReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_support_confirmation_request_report(
    path: str | Path,
    report: LambdaSupportConfirmationRequestReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

