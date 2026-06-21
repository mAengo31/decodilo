from decodilo.runtime.bottleneck_report import bounded_fraction, top_components_by_value


def test_top_components_are_stable_and_descending() -> None:
    ranked = top_components_by_value({"merge": 2.0, "encode": 2.0, "train": 3.0, "missing": None})

    assert ranked == [
        {"component": "train", "value": 3.0},
        {"component": "encode", "value": 2.0},
        {"component": "merge", "value": 2.0},
    ]


def test_bounded_fraction_handles_missing_and_bounds() -> None:
    assert bounded_fraction(None, 10.0) is None
    assert bounded_fraction(1.0, 0.0) == 0.0
    assert bounded_fraction(3.0, 2.0) == 1.0
    assert bounded_fraction(1.0, 4.0) == 0.25

