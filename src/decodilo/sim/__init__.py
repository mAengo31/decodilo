"""CPU-only simulation helpers.

Import concrete runner objects from ``decodilo.sim.runner`` to avoid eager
cross-package imports during syncer initialization.
"""

__all__ = ["runner", "fake_model", "chaos", "metrics"]
