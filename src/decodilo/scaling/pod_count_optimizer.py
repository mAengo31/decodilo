"""Explainable learner-pod count optimization."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.scaling.algorithmic_efficiency_model import (
    AlgorithmicEfficiencyPolicy,
    estimate_algorithmic_efficiency,
)
from decodilo.scaling.artifact_pressure_model import estimate_artifact_pressure
from decodilo.scaling.bandwidth_pressure_model import estimate_bandwidth_pressure
from decodilo.scaling.failure_model import LearnerFailureModel
from decodilo.scaling.goodput_model import estimate_goodput
from decodilo.scaling.infra_overhead_model import combine_infra_overhead
from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.pod_cost_model import estimate_pod_cost
from decodilo.scaling.syncer_pressure_model import estimate_syncer_pressure

Objective = Literal[
    "minimize_cost_per_adjusted_token",
    "maximize_useful_tokens_per_second",
    "minimize_wall_clock_time",
    "minimize_cost_per_useful_token",
    "stay_under_bandwidth_cap",
]


class PodScalingCandidateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_count: int
    total_gpus: float
    raw_tokens_per_second: float
    accepted_tokens_per_second: float
    useful_tokens_per_second: float
    sample_efficiency_adjusted_tokens_per_second: float
    estimated_goodput_ratio: float
    algorithmic_efficiency_multiplier: float
    infra_efficiency_multiplier: float
    syncer_saturation_ratio: float
    artifact_backend_saturation_ratio: float
    bandwidth_saturation_ratio: float
    raw_cost_per_hour: float
    cost_per_total_token: float | None
    cost_per_useful_token: float | None
    cost_per_sample_efficiency_adjusted_token: float | None
    estimated_time_to_target_tokens: float | None
    estimated_cost_to_target_tokens: float | None
    dominant_bottleneck: str
    rejected: bool = False
    warnings: list[str] = Field(default_factory=list)
    artifact_pressure: dict[str, float | int | str | list[str]] = Field(default_factory=dict)
    bandwidth_pressure: dict[str, float | int | str | list[str] | None] = Field(
        default_factory=dict
    )
    syncer_pressure: dict[str, float | int | str | list[str]] = Field(default_factory=dict)


class PodCountOptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    objective: Objective
    recommended_learner_count: int | None
    recommended_candidate: PodScalingCandidateResult | None
    candidates: list[PodScalingCandidateResult]
    pareto_frontier: list[PodScalingCandidateResult]
    rejected_candidates: list[PodScalingCandidateResult]
    decision_rationale: list[str] = Field(default_factory=list)
    sensitivity_summary: dict[str, str | float | int | None] = Field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def optimize_pod_count(
    scenario: LearnerPodScalingScenario,
    *,
    objective: Objective = "minimize_cost_per_adjusted_token",
) -> PodCountOptimizationResult:
    profile = scenario.calibration_profile
    per_gpu_token_rate = float(profile.get("per_gpu_token_rate", 1000.0))
    failure_model = LearnerFailureModel(
        failure_rate_per_hour=float(profile.get("failure_rate_per_hour", 0.0)),
        recovery_time_seconds=float(profile.get("recovery_time_seconds", 0.0)),
        preemption_rate_per_hour=float(profile.get("preemption_rate_per_hour", 0.0)),
        learner_startup_time_seconds=float(profile.get("learner_startup_time_seconds", 0.0)),
        training_duration_hours=scenario.training_duration_hours,
    )
    price_per_gpu_hour = float(profile.get("price_per_gpu_hour", 1.0))
    speed_variance = float(profile.get("speed_variance_coefficient", 0.0))
    max_staleness = int(profile.get("max_staleness_versions", 1))
    token_weighting = bool(profile.get("token_weighting_enabled", True))
    compression_bits = profile.get("compression_bits")
    candidates = [
        _evaluate_candidate(
            scenario=scenario,
            learner_count=count,
            per_gpu_token_rate=per_gpu_token_rate,
            failure_model=failure_model,
            price_per_gpu_hour=price_per_gpu_hour,
            speed_variance=speed_variance,
            max_staleness=max_staleness,
            token_weighting=token_weighting,
            compression_bits=int(compression_bits) if compression_bits is not None else None,
        )
        for count in scenario.candidate_learner_counts
    ]
    rejected = [candidate for candidate in candidates if candidate.rejected]
    viable = [candidate for candidate in candidates if not candidate.rejected]
    recommended = _select_candidate(viable, objective)
    rationale = []
    if recommended is None:
        rationale.append("no candidate satisfied hard pressure constraints")
    else:
        rationale.append(
            f"selected {recommended.learner_count} learners for objective {objective}"
        )
        rationale.append(f"dominant bottleneck: {recommended.dominant_bottleneck}")
    return PodCountOptimizationResult(
        objective=objective,
        recommended_learner_count=(
            recommended.learner_count if recommended is not None else None
        ),
        recommended_candidate=recommended,
        candidates=candidates,
        pareto_frontier=_pareto_frontier(viable),
        rejected_candidates=rejected,
        decision_rationale=rationale,
        sensitivity_summary={
            "candidate_count": len(candidates),
            "rejected_count": len(rejected),
            "per_gpu_token_rate": per_gpu_token_rate,
            "price_per_gpu_hour": price_per_gpu_hour,
        },
    )


def _evaluate_candidate(
    *,
    scenario: LearnerPodScalingScenario,
    learner_count: int,
    per_gpu_token_rate: float,
    failure_model: LearnerFailureModel,
    price_per_gpu_hour: float,
    speed_variance: float,
    max_staleness: int,
    token_weighting: bool,
    compression_bits: int | None,
) -> PodScalingCandidateResult:
    total_gpus = scenario.total_gpus_for(learner_count)
    per_learner_token_rate = total_gpus * per_gpu_token_rate / learner_count
    min_quorum = scenario.min_quorum_for(learner_count)
    grace = scenario.grace_window_seconds_for(learner_count)
    goodput = estimate_goodput(
        learner_count=learner_count,
        min_quorum=min_quorum,
        per_learner_token_rate=per_learner_token_rate,
        failure_model=failure_model,
        grace_window_seconds=grace,
        speed_variance_coefficient=speed_variance,
    )
    model_params = scenario.model_parameter_count or 1
    bytes_per_param = scenario.bytes_per_parameter or 4
    artifact = estimate_artifact_pressure(
        learner_count=learner_count,
        model_parameter_count=model_params,
        bytes_per_parameter=bytes_per_param,
        fragment_count=scenario.fragment_count,
        chunk_size_bytes=scenario.chunk_size_bytes,
        sync_interval_steps=scenario.sync_interval_steps,
        local_step_seconds=scenario.local_step_seconds,
        artifact_backend_read_gbps=scenario.artifact_backend_read_gbps,
        artifact_backend_write_gbps=scenario.artifact_backend_write_gbps,
    )
    bandwidth = estimate_bandwidth_pressure(
        learner_count=learner_count,
        model_parameter_count=model_params,
        bytes_per_parameter=bytes_per_param,
        fragment_count=scenario.fragment_count,
        sync_interval_steps=scenario.sync_interval_steps,
        local_step_seconds=scenario.local_step_seconds,
        bandwidth_cap_gbps=scenario.bandwidth_cap_gbps,
        compression_bits=compression_bits,
    )
    syncer = estimate_syncer_pressure(
        learner_count=learner_count,
        model_parameter_count=model_params,
        bytes_per_parameter=bytes_per_param,
        chunk_size_bytes=scenario.chunk_size_bytes,
        sync_interval_steps=scenario.sync_interval_steps,
        local_step_seconds=scenario.local_step_seconds,
        syncer_max_merge_gbps=scenario.syncer_max_merge_gbps,
    )
    infra = combine_infra_overhead(artifact=artifact, bandwidth=bandwidth, syncer=syncer)
    algo = estimate_algorithmic_efficiency(
        learner_count=learner_count,
        min_quorum=min_quorum,
        grace_window_seconds=grace,
        sync_interval_steps=scenario.sync_interval_steps,
        max_staleness_versions=max_staleness,
        accepted_contribution_ratio=goodput.accepted_contribution_ratio,
        learner_speed_variance=speed_variance,
        policy=AlgorithmicEfficiencyPolicy(token_weighting_enabled=token_weighting),
    )
    useful = goodput.useful_tokens_per_second * infra.infra_efficiency_multiplier
    adjusted = useful * algo.sample_efficiency_multiplier
    cost = estimate_pod_cost(
        learner_count=learner_count,
        total_gpus=total_gpus,
        price_per_gpu_hour=price_per_gpu_hour,
        raw_tokens_per_second=goodput.raw_tokens_per_second,
        useful_tokens_per_second=useful,
        adjusted_tokens_per_second=adjusted,
        target_useful_tokens=scenario.target_useful_tokens,
    )
    ratios = [
        artifact.artifact_backend_saturation_ratio,
        bandwidth.bandwidth_saturation_ratio,
        syncer.syncer_saturation_ratio,
    ]
    rejected = any(ratio > 1.0 for ratio in ratios)
    warnings = [*artifact.warnings, *bandwidth.warnings, *syncer.warnings, *infra.warnings]
    warnings.extend(algo.warnings)
    warnings.extend(cost.warnings)
    if rejected:
        warnings.append("candidate rejected because a configured cap is exceeded")
    return PodScalingCandidateResult(
        learner_count=learner_count,
        total_gpus=total_gpus,
        raw_tokens_per_second=goodput.raw_tokens_per_second,
        accepted_tokens_per_second=goodput.accepted_tokens_per_second,
        useful_tokens_per_second=useful,
        sample_efficiency_adjusted_tokens_per_second=adjusted,
        estimated_goodput_ratio=goodput.estimated_goodput_ratio,
        algorithmic_efficiency_multiplier=algo.sample_efficiency_multiplier,
        infra_efficiency_multiplier=infra.infra_efficiency_multiplier,
        syncer_saturation_ratio=syncer.syncer_saturation_ratio,
        artifact_backend_saturation_ratio=artifact.artifact_backend_saturation_ratio,
        bandwidth_saturation_ratio=bandwidth.bandwidth_saturation_ratio,
        raw_cost_per_hour=cost.raw_cost_per_hour,
        cost_per_total_token=cost.cost_per_total_token,
        cost_per_useful_token=cost.cost_per_useful_token,
        cost_per_sample_efficiency_adjusted_token=(
            cost.cost_per_sample_efficiency_adjusted_token
        ),
        estimated_time_to_target_tokens=cost.estimated_time_to_target_tokens,
        estimated_cost_to_target_tokens=cost.estimated_cost_to_target_tokens,
        dominant_bottleneck=infra.dominant_bottleneck,
        rejected=rejected,
        warnings=warnings,
        artifact_pressure=artifact.model_dump(mode="json"),
        bandwidth_pressure=bandwidth.model_dump(mode="json"),
        syncer_pressure=syncer.model_dump(mode="json"),
    )


def _select_candidate(
    candidates: list[PodScalingCandidateResult],
    objective: Objective,
) -> PodScalingCandidateResult | None:
    if not candidates:
        return None
    if objective == "maximize_useful_tokens_per_second":
        return max(candidates, key=lambda item: item.useful_tokens_per_second)
    if objective == "minimize_wall_clock_time":
        return min(
            candidates,
            key=lambda item: item.estimated_time_to_target_tokens
            if item.estimated_time_to_target_tokens is not None
            else float("inf"),
        )
    if objective == "minimize_cost_per_useful_token":
        return min(
            candidates,
            key=lambda item: item.cost_per_useful_token
            if item.cost_per_useful_token is not None
            else float("inf"),
        )
    if objective == "stay_under_bandwidth_cap":
        return max(
            candidates,
            key=lambda item: (
                item.bandwidth_saturation_ratio <= 1.0,
                item.useful_tokens_per_second,
            ),
        )
    return min(
        candidates,
        key=lambda item: item.cost_per_sample_efficiency_adjusted_token
        if item.cost_per_sample_efficiency_adjusted_token is not None
        else float("inf"),
    )


def _pareto_frontier(
    candidates: list[PodScalingCandidateResult],
) -> list[PodScalingCandidateResult]:
    frontier: list[PodScalingCandidateResult] = []
    for candidate in candidates:
        dominated = False
        candidate_cost = candidate.cost_per_sample_efficiency_adjusted_token or float("inf")
        for other in candidates:
            if other is candidate:
                continue
            other_cost = other.cost_per_sample_efficiency_adjusted_token or float("inf")
            if (
                other.sample_efficiency_adjusted_tokens_per_second
                >= candidate.sample_efficiency_adjusted_tokens_per_second
                and other_cost <= candidate_cost
                and (
                    other.sample_efficiency_adjusted_tokens_per_second
                    > candidate.sample_efficiency_adjusted_tokens_per_second
                    or other_cost < candidate_cost
                )
            ):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)
    return frontier

