from collections.abc import Mapping
from typing import Any

from backend.app.ai.types import HintLevel, PedagogyMetadata, StudentState


def _clamp_hint(value: int, *, maximum: int) -> HintLevel:
    return HintLevel(max(1, min(maximum, value)))


def compute_hint_levels(
    *,
    programming_difficulty: int,
    maths_difficulty: int,
    state: StudentState,
    same_problem: bool,
) -> tuple[HintLevel, HintLevel]:
    if same_problem:
        return (
            _clamp_hint(state.programming_hint_level + 1, maximum=5),
            _clamp_hint(state.maths_hint_level + 1, maximum=5),
        )

    programming_gap = programming_difficulty - round(state.effective_programming_level)
    maths_gap = maths_difficulty - round(state.effective_maths_level)
    return (
        _clamp_hint(1 + programming_gap, maximum=4),
        _clamp_hint(1 + maths_gap, maximum=4),
    )


def update_effective_level(
    *,
    current_level: float,
    difficulty: int,
    final_hint_level: HintLevel,
) -> float:
    safe_current = max(1.0, min(5.0, current_level))
    safe_difficulty = max(1, min(5, difficulty))
    demonstrated_level = safe_difficulty * (6 - final_hint_level) / 5
    learning_rate = 0.2 * min(1.0, safe_difficulty / safe_current)
    updated = safe_current * (1 - learning_rate) + demonstrated_level * learning_rate
    return max(1.0, min(5.0, updated))


def coerce_pedagogy_metadata(
    raw: Mapping[str, Any],
    *,
    has_previous_exchange: bool,
) -> PedagogyMetadata:
    required = {
        "same_problem",
        "is_elaboration",
        "programming_difficulty",
        "maths_difficulty",
    }
    if not required.issubset(raw):
        raise ValueError("Missing pedagogy metadata fields")

    same_problem = raw["same_problem"]
    is_elaboration = raw["is_elaboration"]
    programming = raw["programming_difficulty"]
    maths = raw["maths_difficulty"]
    if not isinstance(same_problem, bool) or not isinstance(is_elaboration, bool):
        raise ValueError("Pedagogy flags must be boolean")
    if isinstance(programming, bool) or not isinstance(programming, int):
        raise ValueError("Programming difficulty must be an integer")
    if isinstance(maths, bool) or not isinstance(maths, int):
        raise ValueError("Maths difficulty must be an integer")

    if not has_previous_exchange:
        same_problem = False
        is_elaboration = False
    elif not same_problem:
        is_elaboration = False

    return PedagogyMetadata(
        same_problem=same_problem,
        is_elaboration=is_elaboration,
        programming_difficulty=max(1, min(5, programming)),
        maths_difficulty=max(1, min(5, maths)),
    )
