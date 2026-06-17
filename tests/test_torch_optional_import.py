import sys

import pytest

from decodilo.errors import OptionalDependencyMissing
from decodilo.trainer.torch_optional import require_torch, torch_available


def test_torch_is_not_imported_by_optional_helper_module_import() -> None:
    if not torch_available():
        assert "torch" not in sys.modules


def test_require_torch_has_clear_error_when_absent() -> None:
    if torch_available():
        assert require_torch().__name__ == "torch"
    else:
        with pytest.raises(OptionalDependencyMissing):
            require_torch()
