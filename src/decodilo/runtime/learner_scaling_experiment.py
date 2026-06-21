"""Short local learner-count experiments for scaling-model calibration."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.runtime.local_runner import LocalRunConfig
from decodilo.runtime.perf_characterization import characterize_local_runtime


class LearnerScalingLocalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_count: int
    report_path: str
    passed: bool
    observed_useful_tokens_per_second: float | None = None
    observed_artifact_bytes: int | None = None
    observed_merge_time_seconds: float | None = None
    observed_checkpoint_time_seconds: float | None = None
    observed_replay_time_seconds: float | None = None
    observed_process_overhead_seconds: float | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class LearnerScalingLocalReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    candidate_results: list[LearnerScalingLocalCase]
    cases_requested: int
    cases_completed: int
    cases_failed: int
    warnings: list[str] = Field(default_factory=list)
    cloud_state: dict[str, bool] = Field(
        default_factory=lambda: {"launch_ready": False, "launch_allowed": False}
    )

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def parse_candidate_learners(value: str) -> list[int]:
    learners = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not learners or any(item <= 0 for item in learners):
        raise ValueError("candidate learners must be positive integers")
    return learners


def run_learner_scaling_local(
    *,
    workdir: str | Path,
    candidate_learners: str | list[int],
    steps: int,
    min_quorum_ratio: float,
    trainer: str,
    payload_storage_mode: str,
    global_update_storage_mode: str,
    checkpoint_storage_mode: str,
    merge_mode: str,
    fragment_artifact_codec: str,
    tensor_artifact_codec: str,
    checkpoint_artifact_codec: str,
    out: str | Path,
) -> LearnerScalingLocalReport:
    learners = (
        parse_candidate_learners(candidate_learners)
        if isinstance(candidate_learners, str)
        else candidate_learners
    )
    if steps <= 0 or not 0 < min_quorum_ratio <= 1:
        raise ValueError("steps must be positive and min_quorum_ratio must be in (0, 1]")
    root = Path(workdir)
    results: list[LearnerScalingLocalCase] = []
    for index, learner_count in enumerate(learners):
        case_dir = root / f"learners-{learner_count}"
        report_path = case_dir / "perf_characterization.json"
        quorum = max(1, round(learner_count * min_quorum_ratio))
        config = LocalRunConfig(
            learners=learner_count,
            steps=steps,
            min_quorum=quorum,
            seed=123,
            workdir=case_dir,
            report_json=case_dir / "report.json",
            vector_dim=8,
            fragments=1,
            local_steps_per_sync=max(1, min(10, steps)),
            trainer_type=trainer,
            payload_storage_mode=payload_storage_mode,
            global_update_storage_mode=global_update_storage_mode,
            checkpoint_storage_mode=checkpoint_storage_mode,
            merge_mode=merge_mode,
            fragment_artifact_codec=fragment_artifact_codec,
            tensor_artifact_codec=tensor_artifact_codec,
            checkpoint_artifact_codec=checkpoint_artifact_codec,
            chunk_size_bytes=1024 * 1024,
            memory_budget_mb=16,
            allow_spill_to_disk=True,
            syncer_checkpoint_interval_rounds=1,
            run_id=f"learner-scaling-local-{index}",
        )
        try:
            perf = characterize_local_runtime(
                config=config,
                out=report_path,
                profile_name="learner_scaling_local",
            )
            passed = all(perf.validation.values())
            results.append(
                LearnerScalingLocalCase(
                    learner_count=learner_count,
                    report_path=str(report_path),
                    passed=passed,
                    observed_useful_tokens_per_second=perf.derived.get(
                        "useful_tokens_per_second"
                    ),
                    observed_artifact_bytes=perf.bytes.get("artifact_bytes_written"),
                    observed_merge_time_seconds=perf.timing.get("merge_wall_time_seconds"),
                    observed_checkpoint_time_seconds=perf.timing.get(
                        "checkpoint_write_wall_time_seconds"
                    ),
                    observed_replay_time_seconds=perf.timing.get("replay_wall_time_seconds"),
                    observed_process_overhead_seconds=perf.timing.get(
                        "total_wall_time_seconds"
                    ),
                    warnings=[
                        "local-only calibration; not proof of cloud or remote backend behavior"
                    ],
                )
            )
        except Exception as exc:  # noqa: BLE001 - experiment records failed cases
            results.append(
                LearnerScalingLocalCase(
                    learner_count=learner_count,
                    report_path=str(report_path),
                    passed=False,
                    error=str(exc),
                )
            )
    report = LearnerScalingLocalReport(
        candidate_results=results,
        cases_requested=len(results),
        cases_completed=sum(1 for result in results if result.passed),
        cases_failed=sum(1 for result in results if not result.passed),
        warnings=[
            "local process overhead is for calibration only and may not extrapolate to cloud"
        ],
    )
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
    return report

