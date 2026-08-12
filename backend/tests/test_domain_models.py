from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest


def test_user_normalizes_identity_and_initializes_effective_levels() -> None:
    from backend.app.ai.types import HintLevel
    from backend.app.domain.models import User

    now = datetime(2026, 8, 12, tzinfo=UTC)
    user = User.create(
        email=" Student@Example.COM ",
        username="Student_1",
        password_hash="argon2-hash",
        self_programming_level=2,
        self_maths_level=4,
        now=now,
    )

    assert user.email == "student@example.com"
    assert user.username == "Student_1"
    assert user.username_key == "student_1"
    assert user.effective_programming_level == 2.0
    assert user.effective_maths_level == 4.0
    assert user.programming_hint_level is HintLevel.SOCRATIC
    assert user.maths_hint_level is HintLevel.SOCRATIC
    assert user.created_at == now
    assert user.updated_at == now


@pytest.mark.parametrize("value", [0, 6, True, 2.5])
def test_self_levels_reject_invalid_values(value: object) -> None:
    from backend.app.domain.models import User

    with pytest.raises(ValueError, match="^level must be an integer from 1 to 5$"):
        User.create(
            email="student@example.com",
            username="student",
            password_hash="hash",
            self_programming_level=value,
            self_maths_level=3,
        )


def test_user_create_generates_uuid_and_aware_utc_timestamp_by_default() -> None:
    from backend.app.domain.models import User

    first = User.create(
        email="first@example.com",
        username="first",
        password_hash="hash",
        self_programming_level=1,
        self_maths_level=1,
    )
    second = User.create(
        email="second@example.com",
        username="second",
        password_hash="hash",
        self_programming_level=1,
        self_maths_level=1,
    )

    assert isinstance(first.id, UUID)
    assert first.id != second.id
    assert first.created_at.tzinfo is UTC
    assert first.updated_at == first.created_at


def test_user_create_rejects_naive_or_non_utc_time() -> None:
    from backend.app.domain.models import User

    common = {
        "email": "student@example.com",
        "username": "student",
        "password_hash": "hash",
        "self_programming_level": 3,
        "self_maths_level": 3,
    }
    for now in (
        datetime(2026, 8, 12),
        datetime(2026, 8, 12, tzinfo=timezone(timedelta(hours=1))),
    ):
        with pytest.raises(ValueError, match="^timestamp must be aware UTC$"):
            User.create(**common, now=now)


def test_domain_records_are_immutable_and_reject_non_utc_timestamps() -> None:
    from backend.app.ai.types import HintLevel
    from backend.app.domain.models import (
        AuthToken,
        ChatMessage,
        ChatSession,
        MessageRole,
        ProblemAssessment,
    )

    now = datetime(2026, 8, 12, tzinfo=UTC)
    assessment = ProblemAssessment(3, 4, same_problem=False, is_elaboration=False)
    session = ChatSession(uuid4(), uuid4(), "Algorithms", now, now)
    message = ChatMessage(
        uuid4(),
        session.id,
        MessageRole.ASSISTANT,
        "Try an invariant.",
        now,
        assessment=assessment,
        programming_hint_level=HintLevel.CONCEPTUAL,
    )
    token = AuthToken("digest", session.user_id, now, now)

    with pytest.raises(FrozenInstanceError):
        message.content = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="^timestamp must be aware UTC$"):
        ChatSession(uuid4(), uuid4(), None, datetime(2026, 8, 12), now)

    assert token.expires_at == now


def test_domain_errors_expose_only_stable_code_and_safe_message() -> None:
    from backend.app.domain.errors import (
        AuthenticationError,
        ConflictError,
        DomainError,
        NotFoundError,
        UpstreamInvalidResponseError,
        UpstreamUnavailableError,
    )

    for error_type in (
        AuthenticationError,
        ConflictError,
        NotFoundError,
        UpstreamInvalidResponseError,
        UpstreamUnavailableError,
    ):
        error = error_type("stable_code", "Safe message")
        assert isinstance(error, DomainError)
        assert error.code == "stable_code"
        assert error.safe_message == "Safe message"
        assert str(error) == "Safe message"
