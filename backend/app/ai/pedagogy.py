from backend.app.ai.types import HintLevel, StudentState


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
