from datetime import timedelta

import pytest

from backend.app.domain.errors import AuthenticationError, ConflictError
from backend.app.security import (
    digest_token,
    hash_password,
    token_digest_matches,
    verify_password,
)
from backend.app.services.auth import AuthService


def test_security_helpers_hash_passwords_and_compare_token_digests() -> None:
    password = "fixture password that is long enough"
    token = "fixture-token-not-a-secret"
    password_hash = hash_password(password)

    assert password not in password_hash
    assert verify_password(password, password_hash)
    assert token_digest_matches(token, digest_token(token))
    assert not token_digest_matches("different-token", digest_token(token))


@pytest.mark.asyncio
async def test_register_hashes_password_and_login_stores_only_digest(
    auth_service: AuthService,
    store,
) -> None:
    password = "fixture password that is long enough"
    user = await auth_service.register(
        email="student@example.com",
        username="student",
        password=password,
        self_programming_level=2,
        self_maths_level=3,
    )

    stored_user = await store.users.get(user.id)
    assert stored_user is not None
    assert password not in stored_user.password_hash

    issued = await auth_service.login(email="student@example.com", password=password)
    stored_token = await store.tokens.get_by_digest(digest_token(issued.token))

    assert issued.token
    assert stored_token is not None
    assert stored_token.token_digest == digest_token(issued.token)
    assert stored_token.token_digest != issued.token
    assert await auth_service.authenticate(issued.token) == user


@pytest.mark.asyncio
async def test_login_unknown_email_and_wrong_password_have_the_same_error(
    auth_service: AuthService,
) -> None:
    password = "fixture password that is long enough"
    await auth_service.register(
        email="student@example.com",
        username="student",
        password=password,
        self_programming_level=2,
        self_maths_level=3,
    )

    with pytest.raises(AuthenticationError) as missing_email:
        await auth_service.login(email="missing@example.com", password=password)
    with pytest.raises(AuthenticationError) as wrong_password:
        await auth_service.login(email="student@example.com", password="another fixture password")

    assert (missing_email.value.code, missing_email.value.safe_message) == (
        wrong_password.value.code,
        wrong_password.value.safe_message,
    ) == ("invalid_credentials", "Invalid email or password")


@pytest.mark.asyncio
async def test_logout_revokes_only_current_token(auth_service: AuthService) -> None:
    password = "fixture password that is long enough"
    await auth_service.register(
        email="student@example.com",
        username="student",
        password=password,
        self_programming_level=2,
        self_maths_level=3,
    )
    first = await auth_service.login(email="student@example.com", password=password)
    second = await auth_service.login(email="student@example.com", password=password)

    await auth_service.logout(first.token)

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        await auth_service.authenticate(first.token)
    assert await auth_service.authenticate(second.token)


@pytest.mark.asyncio
async def test_expired_token_is_deleted_and_rejected(store, fixed_now) -> None:
    clock_now = fixed_now
    service = AuthService(
        users=store.users,
        tokens=store.tokens,
        clock=lambda: clock_now,
        token_ttl=timedelta(seconds=1),
        token_factory=lambda: "fixture-token-not-a-secret",
    )
    password = "fixture password that is long enough"
    await service.register(
        email="student@example.com",
        username="student",
        password=password,
        self_programming_level=2,
        self_maths_level=3,
    )
    issued = await service.login(email="student@example.com", password=password)
    clock_now = fixed_now + timedelta(seconds=1)

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        await service.authenticate(issued.token)
    assert await store.tokens.get_by_digest(digest_token(issued.token)) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [None, "", "unknown-token"])
async def test_missing_or_unknown_token_is_rejected(
    auth_service: AuthService, token: str | None
) -> None:
    with pytest.raises(AuthenticationError) as failure:
        await auth_service.authenticate(token)

    assert (failure.value.code, failure.value.safe_message) == (
        "invalid_token",
        "Invalid or expired token",
    )


@pytest.mark.asyncio
async def test_register_preserves_repository_uniqueness_conflicts(
    auth_service: AuthService,
) -> None:
    password = "fixture password that is long enough"
    await auth_service.register(
        email="student@example.com",
        username="student",
        password=password,
        self_programming_level=2,
        self_maths_level=3,
    )

    with pytest.raises(ConflictError, match="Email already exists"):
        await auth_service.register(
            email=" STUDENT@example.com ",
            username="other",
            password=password,
            self_programming_level=2,
            self_maths_level=3,
        )
