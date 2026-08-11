from dataclasses import FrozenInstanceError

import pytest


def test_hint_and_difficulty_ranges_are_explicit() -> None:
    from backend.app.ai.types import Difficulty, HintLevel

    assert HintLevel.SOCRATIC.value == 1
    assert HintLevel.FULL_SOLUTION.value == 5
    assert Difficulty.INTRODUCTORY.value == 1
    assert Difficulty.EXPERT.value == 5


def test_student_state_is_immutable() -> None:
    from backend.app.ai.types import HintLevel, StudentState

    state = StudentState(
        effective_programming_level=2.0,
        effective_maths_level=3.0,
        programming_hint_level=HintLevel.SOCRATIC,
        maths_hint_level=HintLevel.CONCEPTUAL,
    )

    with pytest.raises(FrozenInstanceError):
        state.effective_programming_level = 4.0  # type: ignore[misc]
