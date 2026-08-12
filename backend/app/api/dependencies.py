from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import Settings
from backend.app.domain.models import User
from backend.app.memory import InMemoryStore
from backend.app.services.auth import AuthService
from backend.app.services.chat import ChatService

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AppContainer:
    auth_service: AuthService
    chat_service: ChatService


def create_default_container(settings: Settings | None = None) -> AppContainer:
    resolved_settings = Settings.from_env() if settings is None else settings
    store = InMemoryStore()
    return AppContainer(
        auth_service=AuthService(
            users=store.users,
            tokens=store.tokens,
            clock=lambda: datetime.now(UTC),
            token_ttl=resolved_settings.token_ttl_seconds,
        ),
        chat_service=ChatService(
            sessions=store.sessions,
            messages=store.messages,
            clock=lambda: datetime.now(UTC),
        ),
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> User:
    token = None if credentials is None else credentials.credentials
    return await container.auth_service.authenticate(token)
