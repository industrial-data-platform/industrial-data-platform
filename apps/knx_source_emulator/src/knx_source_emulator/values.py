from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from knx_source_emulator.plan import EmulatorPoint


@dataclass(frozen=True)
class GeneratedValue:
    value: object
    value_raw: str


class ValueGenerator:
    def __init__(self, *, seed: int) -> None:
        self._seed = seed
        self._sequences: dict[str, int] = {}

    def next_value(self, point: EmulatorPoint, *, now: datetime) -> GeneratedValue:
        del now
        sequence = self._sequences.get(point.point_key, 0)
        self._sequences[point.point_key] = sequence + 1
        if point.value_type == "number":
            return self._number_value(point, sequence)
        if point.value_type == "boolean":
            return self._boolean_value(point, sequence)
        if point.value_type == "string":
            return self._string_value(point, sequence)
        return GeneratedValue(value=None, value_raw="null")

    def _number_value(self, point: EmulatorPoint, sequence: int) -> GeneratedValue:
        parameters = point.profile.parameters
        base = float(parameters.get("base", 0.0))
        threshold = point.change_threshold
        step = threshold if threshold is not None and threshold > 0 else 1.0
        value = round(base + (sequence * step), 3)
        return GeneratedValue(value=value, value_raw=str(value))

    def _boolean_value(self, point: EmulatorPoint, sequence: int) -> GeneratedValue:
        true_ratio = float(point.profile.parameters.get("true_ratio", 0.5))
        period = max(2, round(1 / true_ratio)) if 0 < true_ratio < 1 else 2
        offset = self._seed % period
        value = (sequence + offset) % period == 0
        return GeneratedValue(value=value, value_raw="true" if value else "false")

    def _string_value(self, point: EmulatorPoint, sequence: int) -> GeneratedValue:
        values = point.profile.parameters.get("values")
        if not isinstance(values, list) or not values:
            text = "норма"
        else:
            text = str(values[(sequence + self._seed) % len(values)])
        return GeneratedValue(value=text, value_raw=text)
