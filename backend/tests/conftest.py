from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from backend.app.domain.models import User


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


@pytest.fixture
def user_factory(fixed_now: datetime) -> Callable[..., User]:
    def build(**overrides: object) -> User:
        values: dict[str, object] = {
            "email": "student@example.com",
            "username": "student",
            "password_hash": "argon2-hash",
            "self_programming_level": 2,
            "self_maths_level": 3,
            "now": fixed_now,
        }
        values.update(overrides)
        return User.create(**values)  # type: ignore[arg-type]

    return build
