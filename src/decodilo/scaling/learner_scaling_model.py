"""Convenience entry points for learner-pod scaling decisions."""

from __future__ import annotations

from decodilo.scaling.learner_pods import LearnerPodScalingScenario
from decodilo.scaling.pod_count_optimizer import Objective, optimize_pod_count
from decodilo.scaling.scaling_report import (
    LearnerScalingDecisionReport,
    build_scaling_decision_report,
)


def evaluate_learner_scaling(
    scenario: LearnerPodScalingScenario,
    *,
    objective: Objective = "minimize_cost_per_adjusted_token",
) -> LearnerScalingDecisionReport:
    return build_scaling_decision_report(
        scenario=scenario,
        optimization=optimize_pod_count(scenario, objective=objective),
    )

