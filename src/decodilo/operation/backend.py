"""Operation backend protocol for the pathway layer."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from decodilo.operation.result import OperationResult
from decodilo.operation.spec import OperationSpec


@runtime_checkable
class OperationBackend(Protocol):
    """Pluggable execution backend for an :class:`OperationSpec`.

    A backend maps a backend-agnostic spec onto some concrete execution
    substrate and returns a normalized :class:`OperationResult`. The local
    backend delegates to the real learner/syncer runtime; a future remote
    backend (e.g. Lambda) would implement this same interface.
    """

    name: str

    def run(self, spec: OperationSpec, *, workdir: Path) -> OperationResult:
        """Execute ``spec`` and return a normalized result."""
        ...
