from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from backend.app.domain.models import User
from backend.app.memory import InMemoryStore
from backend.app.services.auth import AuthService


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


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def auth_service(store: InMemoryStore, fixed_now: datetime) -> AuthService:
    return AuthService(
        users=store.users,
        tokens=store.tokens,
        clock=lambda: fixed_now,
        token_ttl=86_400,
    )
