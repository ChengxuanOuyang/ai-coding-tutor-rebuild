from dataclasses import dataclass
from enum import IntEnum


class Difficulty(IntEnum):
    INTRODUCTORY = 1
    ELEMENTARY = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class HintLevel(IntEnum):
    SOCRATIC = 1
    CONCEPTUAL = 2
    STRUCTURAL = 3
    CONCRETE = 4
    FULL_SOLUTION = 5


@dataclass(frozen=True)
class StudentState:
    effective_programming_level: float
    effective_maths_level: float
    programming_hint_level: HintLevel = HintLevel.SOCRATIC
    maths_hint_level: HintLevel = HintLevel.SOCRATIC
