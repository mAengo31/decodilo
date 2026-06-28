"""Operation runner: routes an OperationSpec through a backend."""

from __future__ import annotations

from pathlib import Path

from decodilo.operation.backend import OperationBackend
from decodilo.operation.local_backend import LocalOperationBackend
from decodilo.operation.result import OperationResult
from decodilo.operation.spec import OperationSpec


def run_operation(
    spec: OperationSpec,
    *,
    workdir: str | Path,
    backend: OperationBackend | None = None,
) -> OperationResult:
    """Run ``spec`` on ``backend`` (defaulting to the local runtime backend).

    The runner is intentionally thin: it only selects a backend and delegates.
    All real work happens inside the backend, which for ``local`` is the actual
    learner/syncer runtime.
    """
    selected = backend or LocalOperationBackend()
    return selected.run(spec, workdir=Path(workdir))
