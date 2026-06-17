from decodilo.runtime.trainer_matrix import list_trainers, run_trainer_check, run_trainer_matrix


def test_trainer_list_and_required_matrix(tmp_path) -> None:
    names = {entry["trainer"] for entry in list_trainers(include_optional=True)}

    assert {"numpy_convex", "scripted", "torch_tiny", "torch_causal_lm"} <= names

    check = run_trainer_check(trainer="numpy_convex", workdir=tmp_path)
    assert check["available"] is True
    assert not check["checks_failed"]

    matrix = run_trainer_matrix(workdir=tmp_path, include_optional=False)
    assert matrix.passed is True
    assert (tmp_path / "trainer_matrix.json").exists()


def test_optional_trainers_are_unavailable_or_passing(tmp_path) -> None:
    matrix = run_trainer_matrix(workdir=tmp_path, include_optional=True)

    assert matrix.passed is True
    for result in matrix.results:
        if result.trainer_name.startswith("torch_") and not result.available:
            assert result.checks_skipped == ["all"]

