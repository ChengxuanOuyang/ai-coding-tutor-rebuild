from dataclasses import FrozenInstanceError

import pytest

from backend.app.ai.types import Difficulty, HintLevel, StudentState


def test_hint_and_difficulty_ranges_are_explicit() -> None:
    assert HintLevel.SOCRATIC.value == 1
    assert HintLevel.FULL_SOLUTION.value == 5
    assert Difficulty.INTRODUCTORY.value == 1
    assert Difficulty.EXPERT.value == 5


def test_student_state_is_immutable() -> None:
    state = StudentState(
        effective_programming_level=2.0,
        effective_maths_level=3.0,
        programming_hint_level=HintLevel.SOCRATIC,
        maths_hint_level=HintLevel.CONCEPTUAL,
    )

    with pytest.raises(FrozenInstanceError):
        state.effective_programming_level = 4.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("difficulty", "effective_level", "expected"),
    [
        (1, 3.0, HintLevel.SOCRATIC),
        (3, 3.0, HintLevel.SOCRATIC),
        (4, 3.0, HintLevel.CONCEPTUAL),
        (5, 3.0, HintLevel.STRUCTURAL),
        (5, 1.0, HintLevel.CONCRETE),
    ],
)
def test_new_problem_hint_uses_gap_and_never_starts_at_five(
    difficulty: int,
    effective_level: float,
    expected: HintLevel,
) -> None:
    from backend.app.ai.pedagogy import compute_hint_levels

    state = StudentState(
        effective_programming_level=effective_level,
        effective_maths_level=effective_level,
    )

    programming, maths = compute_hint_levels(
        programming_difficulty=difficulty,
        maths_difficulty=difficulty,
        state=state,
        same_problem=False,
    )

    assert programming is expected
    assert maths is expected
    assert programming is not HintLevel.FULL_SOLUTION


def test_new_problem_computes_each_dimension_independently() -> None:
    from backend.app.ai.pedagogy import compute_hint_levels

    state = StudentState(
        effective_programming_level=1.0,
        effective_maths_level=5.0,
    )

    programming, maths = compute_hint_levels(
        programming_difficulty=5,
        maths_difficulty=1,
        state=state,
        same_problem=False,
    )

    assert programming is HintLevel.CONCRETE
    assert maths is HintLevel.SOCRATIC


def test_same_problem_increments_each_dimension_independently() -> None:
    from backend.app.ai.pedagogy import compute_hint_levels

    state = StudentState(
        effective_programming_level=2.0,
        effective_maths_level=4.0,
        programming_hint_level=HintLevel.CONCEPTUAL,
        maths_hint_level=HintLevel.CONCRETE,
    )

    programming, maths = compute_hint_levels(
        programming_difficulty=5,
        maths_difficulty=1,
        state=state,
        same_problem=True,
    )

    assert programming is HintLevel.STRUCTURAL
    assert maths is HintLevel.FULL_SOLUTION
