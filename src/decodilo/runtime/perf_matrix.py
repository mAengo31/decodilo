"""Small grid runner for local performance characterization."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.runtime.local_runner import LocalRunConfig
from decodilo.runtime.perf_characterization import characterize_local_runtime


class PerfMatrixCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    learners: int
    elements: int
    chunk_size_kb: int


class PerfMatrixReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    cases_requested: int
    cases_completed: int
    cases_failed: int
    case_reports: list[dict[str, Any]] = Field(default_factory=list)
    aggregate_bottlenecks: list[dict[str, Any]] = Field(default_factory=list)
    scaling_observations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def parse_int_list(value: str) -> list[int]:
    parsed = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not parsed:
        raise ValueError("expected at least one integer")
    return parsed


def plan_perf_matrix_cases(
    *,
    learners: str,
    elements: str,
    chunk_size_kb: str,
    max_cases: int,
) -> list[PerfMatrixCase]:
    cases = [
        PerfMatrixCase(learners=learner, elements=element, chunk_size_kb=chunk)
        for learner, element, chunk in itertools.product(
            parse_int_list(learners),
            parse_int_list(elements),
            parse_int_list(chunk_size_kb),
        )
    ]
    if len(cases) > max_cases:
        raise ValueError(f"perf matrix requested {len(cases)} cases, max-cases is {max_cases}")
    return cases


def run_perf_matrix(
    *,
    workdir: str | Path,
    trainer: str,
    learners: str,
    elements: str,
    chunk_size_kb: str,
    steps: int,
    min_quorum: int,
    codec: str,
    out: str | Path,
    max_cases: int = 16,
    dry_run: bool = False,
) -> PerfMatrixReport:
    root = Path(workdir)
    cases = plan_perf_matrix_cases(
        learners=learners,
        elements=elements,
        chunk_size_kb=chunk_size_kb,
        max_cases=max_cases,
    )
    if dry_run:
        report = PerfMatrixReport(
            cases_requested=len(cases),
            cases_completed=0,
            cases_failed=0,
            case_reports=[case.model_dump(mode="json") for case in cases],
            warnings=["dry run; no cases executed"],
        )
        _write(out, report)
        return report

    case_reports: list[dict[str, Any]] = []
    errors: list[str] = []
    component_totals: dict[str, float] = {}
    for index, case in enumerate(cases):
        case_dir = root / f"case-{index:03d}"
        report_path = case_dir / "perf_characterization.json"
        config = LocalRunConfig(
            learners=case.learners,
            steps=steps,
            min_quorum=min_quorum,
            seed=123,
            workdir=case_dir,
            report_json=case_dir / "report.json",
            vector_dim=case.elements,
            fragments=1,
            local_steps_per_sync=max(1, min(10, steps)),
            trainer_type=trainer,
            payload_storage_mode="chunked",
            global_update_storage_mode="chunked",
            checkpoint_storage_mode="chunked",
            merge_mode="streaming_chunked",
            tensor_artifact_codec=codec,
            fragment_artifact_codec=codec,
            checkpoint_artifact_codec=codec,
            chunk_size_bytes=case.chunk_size_kb * 1024,
            memory_budget_mb=16,
            allow_spill_to_disk=True,
            syncer_checkpoint_interval_rounds=1,
            run_id=f"perf-matrix-{index}",
        )
        try:
            perf = characterize_local_runtime(
                config=config,
                out=report_path,
                profile_name="perf_matrix",
            )
            case_payload = {
                "case": case.model_dump(mode="json"),
                "report_path": str(report_path),
                "passed": all(perf.validation.values()),
                "top_component": (
                    perf.bottlenecks["top_components_by_wall_time"][0]
                    if perf.bottlenecks["top_components_by_wall_time"]
                    else None
                ),
            }
            for item in perf.bottlenecks["top_components_by_wall_time"]:
                component_totals[item["component"]] = component_totals.get(
                    item["component"], 0.0
                ) + float(item["value"])
        except Exception as exc:  # noqa: BLE001 - matrix records failed cases
            case_payload = {
                "case": case.model_dump(mode="json"),
                "report_path": str(report_path),
                "passed": False,
                "error": str(exc),
            }
            errors.append(str(exc))
        case_reports.append(case_payload)
    aggregate = [
        {"component": component, "total_wall_time_seconds": value}
        for component, value in sorted(
            component_totals.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    report = PerfMatrixReport(
        cases_requested=len(cases),
        cases_completed=sum(1 for item in case_reports if item.get("passed")),
        cases_failed=sum(1 for item in case_reports if not item.get("passed")),
        case_reports=case_reports,
        aggregate_bottlenecks=aggregate,
        scaling_observations=[
            "local wall-clock timings are machine-specific and are not cloud guarantees"
        ],
        errors=errors,
    )
    _write(out, report)
    return report


def _write(path: str | Path, report: PerfMatrixReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

