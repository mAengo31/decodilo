import pytest

from decodilo.storage.errors import MemoryBudgetExceeded
from decodilo.storage.memory_budget import MemoryBudget


def test_memory_budget_accepts_under_budget_and_tracks_peak() -> None:
    budget = MemoryBudget(max_in_memory_fragment_bytes=10, max_total_in_memory_bytes=20)

    budget.reserve_memory(8)

    assert budget.snapshot().current_in_memory_bytes == 8
    assert budget.snapshot().peak_in_memory_bytes == 8
    budget.release_memory(8)
    assert budget.snapshot().current_in_memory_bytes == 0


def test_memory_budget_rejects_over_budget() -> None:
    budget = MemoryBudget(max_in_memory_fragment_bytes=10, max_total_in_memory_bytes=20)

    with pytest.raises(MemoryBudgetExceeded):
        budget.reserve_memory(11)

