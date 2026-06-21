from lambda_m023_helpers import (
    build_m023_evidence_package_from_refs,
    write_m023_core_artifacts,
)
from pydantic import ValidationError

from decodilo.lambda_cloud.real_mutation_review_record import (
    LambdaRealMutationReviewRecord,
    build_lambda_real_mutation_review_record,
)


def test_review_record_missing_evidence_is_incomplete(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)
    package = build_m023_evidence_package_from_refs(
        refs,
        m019c_discovery=tmp_path / "missing.json",
    )

    record = build_lambda_real_mutation_review_record(evidence_package=package)

    assert record.status == "evidence_incomplete"
    assert record.launch_allowed is False


def test_review_record_complete_package_reaches_design_review_ready(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)
    package = build_m023_evidence_package_from_refs(refs)

    record = build_lambda_real_mutation_review_record(evidence_package=package)

    assert record.status == "design_review_ready"
    assert "real mutation remains disabled" in " ".join(record.warnings)
    assert record.real_mutation_enabled is False


def test_review_record_rejects_enabled_flags(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)
    record = build_lambda_real_mutation_review_record(
        evidence_package=build_m023_evidence_package_from_refs(refs)
    )

    try:
        LambdaRealMutationReviewRecord(
            **record.model_copy(update={"launch_allowed": True}).model_dump()
        )
    except ValidationError as exc:
        assert "cannot enable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("enabled review record accepted")
