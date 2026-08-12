from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.app.domain.errors import NotFoundError
from backend.app.domain.models import ChatMessage, ChatSession
from backend.app.repositories import MessageRepository, SessionRepository


class ChatService:
    def __init__(
        self,
        *,
        sessions: SessionRepository,
        messages: MessageRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sessions = sessions
        self._messages = messages
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)

    async def create_session(self, *, user_id: UUID, title: str | None) -> ChatSession:
        normalized_title = self._normalize_title(title)
        now = self._now()
        session = ChatSession(
            id=uuid4(),
            user_id=user_id,
            title=normalized_title,
            created_at=now,
            updated_at=now,
        )
        await self._sessions.add(session)
        return session

    async def list_sessions(self, *, user_id: UUID) -> list[ChatSession]:
        return await self._sessions.list_for_user(user_id)

    async def list_messages(self, *, user_id: UUID, session_id: UUID) -> list[ChatMessage]:
        session = await self._sessions.get_for_user(session_id, user_id)
        if session is None:
            raise self._session_not_found()
        return await self._messages.list_for_session(session.id)

    @staticmethod
    def _normalize_title(title: str | None) -> str | None:
        if title is None:
            return None
        normalized = title.strip()
        if len(normalized) > 120:
            raise ValueError("session title must be at most 120 characters")
        return normalized or None

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is not UTC:
            raise ValueError("clock must return aware UTC timestamps")
        return now

    @staticmethod
    def _session_not_found() -> NotFoundError:
        return NotFoundError("session_not_found", "Session not found")
