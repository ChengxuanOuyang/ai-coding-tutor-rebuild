from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from backend.app.ai.types import HintLevel


def _require_aware_utc(timestamp: datetime) -> None:
    if timestamp.tzinfo is not UTC:
        raise ValueError("timestamp must be aware UTC")


def _validate_level(level: object) -> int:
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 5:
        raise ValueError("level must be an integer from 1 to 5")
    return level


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ProblemAssessment:
    programming_difficulty: int
    maths_difficulty: int
    same_problem: bool
    is_elaboration: bool


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    username: str
    username_key: str
    password_hash: str
    self_programming_level: int
    self_maths_level: int
    effective_programming_level: float
    effective_maths_level: float
    programming_hint_level: HintLevel
    maths_hint_level: HintLevel
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_aware_utc(self.created_at)
        _require_aware_utc(self.updated_at)

    @classmethod
    def create(
        cls,
        *,
        email: str,
        username: str,
        password_hash: str,
        self_programming_level: object,
        self_maths_level: object,
        now: datetime | None = None,
        id: UUID | None = None,
    ) -> "User":
        programming_level = _validate_level(self_programming_level)
        maths_level = _validate_level(self_maths_level)
        created_at = datetime.now(UTC) if now is None else now
        _require_aware_utc(created_at)
        return cls(
            id=uuid4() if id is None else id,
            email=email.strip().lower(),
            username=username,
            username_key=username.casefold(),
            password_hash=password_hash,
            self_programming_level=programming_level,
            self_maths_level=maths_level,
            effective_programming_level=float(programming_level),
            effective_maths_level=float(maths_level),
            programming_hint_level=HintLevel.SOCRATIC,
            maths_hint_level=HintLevel.SOCRATIC,
            created_at=created_at,
            updated_at=created_at,
        )


@dataclass(frozen=True)
class AuthToken:
    token_digest: str
    user_id: UUID
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _require_aware_utc(self.created_at)
        _require_aware_utc(self.expires_at)


@dataclass(frozen=True)
class ChatSession:
    id: UUID
    user_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_aware_utc(self.created_at)
        _require_aware_utc(self.updated_at)


@dataclass(frozen=True)
class ChatMessage:
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    assessment: ProblemAssessment | None = None
    programming_hint_level: HintLevel | None = None
    maths_hint_level: HintLevel | None = None
    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        _require_aware_utc(self.created_at)
