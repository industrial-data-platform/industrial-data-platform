from __future__ import annotations

from datetime import UTC, datetime

from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
from knx_source_emulator.plan import build_emulator_plan
from knx_source_emulator.values import ValueGenerator


def test_value_generation_respects_change_threshold_for_numeric_points() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(devices=1, tags_per_device=1, seed=2026)
    )
    point = build_emulator_plan(model, host="127.0.0.1", port=0).points[0]
    generator = ValueGenerator(seed=1)

    first = generator.next_value(point, now=datetime(2026, 5, 11, tzinfo=UTC))
    second = generator.next_value(point, now=datetime(2026, 5, 11, tzinfo=UTC))

    assert isinstance(first.value, float)
    assert isinstance(second.value, float)
    assert point.change_threshold is not None
    assert abs(second.value - first.value) >= point.change_threshold


def test_value_generation_cycles_string_profiles() -> None:
    model = generate_synthetic_config(
        GeneratorOptions(devices=1, tags_per_device=6, seed=2026)
    )
    point = next(
        point
        for point in build_emulator_plan(model, host="127.0.0.1", port=0).points
        if point.value_type == "string"
    )
    generator = ValueGenerator(seed=1)

    first = generator.next_value(point, now=datetime(2026, 5, 11, tzinfo=UTC))
    second = generator.next_value(point, now=datetime(2026, 5, 11, tzinfo=UTC))

    assert first.value in point.profile.parameters["values"]
    assert second.value in point.profile.parameters["values"]
    assert second.value != first.value
