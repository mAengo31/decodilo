"""Backend-agnostic operation (pathway) layer for DiLoCo runs.

This package is the minimal "operation layer" that sits above the concrete
learner/syncer runtime. It describes a DiLoCo job declaratively (an
``OperationSpec``), routes it through a pluggable ``OperationBackend``, and
returns a normalized ``OperationResult`` plus a safety envelope.

Design goals:
- Do not reimplement training. The local backend delegates to the real
  ``decodilo.runtime.local_runner.LocalRunner``.
- Keep the backend interface narrow enough that a future remote backend
  (e.g. Lambda) can implement it without touching runtime internals.
- Carry an explicit safety envelope so launch/spend remain disabled by default.
"""

from __future__ import annotations

from decodilo.operation.backend import OperationBackend
from decodilo.operation.lambda_backend import (
    LambdaDryRunOperationBackend,
    LambdaOperationBackend,
    LambdaOperationBackendConfig,
)
from decodilo.operation.local_backend import LocalOperationBackend
from decodilo.operation.pathway import (
    PathwayManagedExperimentPlan,
    build_next_lambda_gpu_chunked_experiment,
    compile_pathway_managed_experiment,
)
from decodilo.operation.result import OperationResult
from decodilo.operation.runner import run_operation
from decodilo.operation.spec import (
    OperationSafetyEnvelope,
    OperationSpec,
)

__all__ = [
    "OperationBackend",
    "LambdaDryRunOperationBackend",
    "LambdaOperationBackend",
    "LambdaOperationBackendConfig",
    "LocalOperationBackend",
    "PathwayManagedExperimentPlan",
    "build_next_lambda_gpu_chunked_experiment",
    "compile_pathway_managed_experiment",
    "OperationSafetyEnvelope",
    "OperationSpec",
    "OperationResult",
    "run_operation",
]
