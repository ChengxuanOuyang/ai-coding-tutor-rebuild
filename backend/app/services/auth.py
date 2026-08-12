from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.app.domain.errors import AuthenticationError
from backend.app.domain.models import AuthToken, User
from backend.app.repositories import TokenRepository, UserRepository
from backend.app.security import (
    create_bearer_token,
    digest_token,
    hash_password,
    token_digest_matches,
    verify_password,
)


@dataclass(frozen=True)
class IssuedToken:
    token: str
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        tokens: TokenRepository,
        clock: Callable[[], datetime],
        token_ttl: int | timedelta,
        token_factory: Callable[[], str] = create_bearer_token,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._clock = clock
        self._token_ttl = (
            timedelta(seconds=token_ttl) if isinstance(token_ttl, int) else token_ttl
        )
        self._token_factory = token_factory

    async def register(
        self,
        *,
        email: str,
        username: str,
        password: str,
        self_programming_level: int,
        self_maths_level: int,
    ) -> User:
        user = User.create(
            email=email,
            username=username,
            password_hash=hash_password(password),
            self_programming_level=self_programming_level,
            self_maths_level=self_maths_level,
            now=self._now(),
        )
        await self._users.add(user)
        return user

    async def login(self, *, email: str, password: str) -> IssuedToken:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("invalid_credentials", "Invalid email or password")

        token = self._token_factory()
        now = self._now()
        expires_at = now + self._token_ttl
        await self._tokens.add(
            AuthToken(
                token_digest=digest_token(token),
                user_id=user.id,
                created_at=now,
                expires_at=expires_at,
            )
        )
        return IssuedToken(token=token, expires_at=expires_at)

    async def authenticate(self, token: str | None) -> User:
        if not token:
            raise self._invalid_token()

        digest = digest_token(token)
        stored_token = await self._tokens.get_by_digest(digest)
        if stored_token is None or not token_digest_matches(token, stored_token.token_digest):
            raise self._invalid_token()
        if stored_token.expires_at <= self._now():
            await self._tokens.delete_by_digest(stored_token.token_digest)
            raise self._invalid_token()

        user = await self._users.get(stored_token.user_id)
        if user is None:
            await self._tokens.delete_by_digest(stored_token.token_digest)
            raise self._invalid_token()
        return user

    async def logout(self, token: str | None) -> None:
        await self.authenticate(token)
        if token is not None:
            await self._tokens.delete_by_digest(digest_token(token))

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is not UTC:
            raise ValueError("clock must return aware UTC timestamps")
        return now

    @staticmethod
    def _invalid_token() -> AuthenticationError:
        return AuthenticationError("invalid_token", "Invalid or expired token")
