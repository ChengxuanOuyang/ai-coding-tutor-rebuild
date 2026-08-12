import asyncio
from datetime import datetime
from uuid import UUID

from backend.app.domain.errors import ConflictError
from backend.app.domain.models import AuthToken, ChatMessage, ChatSession, MessageRole, User


class InMemoryUserRepository:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store

    async def add(self, user: User) -> None:
        self._store._add_user(user)

    async def get(self, user_id: UUID) -> User | None:
        return self._store._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        user_id = self._store._users_by_email.get(email.strip().lower())
        return None if user_id is None else self._store._users[user_id]


class InMemoryTokenRepository:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store

    async def add(self, token: AuthToken) -> None:
        if token.token_digest in self._store._tokens:
            raise ConflictError("token_conflict", "Token already exists")
        self._store._tokens[token.token_digest] = token

    async def get_by_digest(self, token_digest: str) -> AuthToken | None:
        return self._store._tokens.get(token_digest)

    async def delete_by_digest(self, token_digest: str) -> None:
        self._store._tokens.pop(token_digest, None)

    async def delete_expired(self, now: datetime) -> None:
        expired = [
            digest for digest, token in self._store._tokens.items() if token.expires_at <= now
        ]
        for digest in expired:
            del self._store._tokens[digest]


class InMemorySessionRepository:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store

    async def add(self, session: ChatSession) -> None:
        if session.id in self._store._sessions:
            raise ConflictError("session_conflict", "Session already exists")
        self._store._sessions[session.id] = session

    async def get(self, session_id: UUID) -> ChatSession | None:
        return self._store._sessions.get(session_id)

    async def get_for_user(self, session_id: UUID, user_id: UUID) -> ChatSession | None:
        session = self._store._sessions.get(session_id)
        return session if session is not None and session.user_id == user_id else None

    async def list_for_user(self, user_id: UUID) -> list[ChatSession]:
        sessions = (
            session for session in self._store._sessions.values() if session.user_id == user_id
        )
        return sorted(sessions, key=lambda session: (session.created_at, session.id.int))


class InMemoryMessageRepository:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store

    async def add(self, message: ChatMessage) -> None:
        self._store._add_message(message)

    async def list_for_session(self, session_id: UUID) -> list[ChatMessage]:
        messages = (
            message
            for message in self._store._messages.values()
            if message.session_id == session_id
        )
        return sorted(messages, key=lambda message: (message.created_at, message.id.int))


class InMemoryChatUnitOfWork:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store
        self._user: User | None = None
        self._messages: tuple[ChatMessage, ChatMessage] | None = None
        self._committed = False

    async def __aenter__(self) -> "InMemoryChatUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        return None

    def stage_messages(self, user_message: ChatMessage, assistant_message: ChatMessage) -> None:
        is_expected_pair = (
            user_message.role is MessageRole.USER
            and assistant_message.role is MessageRole.ASSISTANT
        )
        if not is_expected_pair:
            raise ValueError("staged messages must be a user and assistant pair")
        if user_message.session_id != assistant_message.session_id:
            raise ValueError("staged messages must belong to the same session")
        self._messages = (user_message, assistant_message)

    def stage_user(self, user: User) -> None:
        self._user = user

    async def commit(self) -> None:
        if self._committed:
            return
        self._validate_staged_changes()
        if self._user is not None:
            self._store._replace_user(self._user)
        if self._messages is not None:
            for message in self._messages:
                self._store._add_message(message)
        self._committed = True

    def _validate_staged_changes(self) -> None:
        if self._user is None or self._messages is None:
            raise ValueError("chat unit of work requires a staged user and message pair")
        if self._user is not None:
            self._store._validate_user_replacement(self._user)
        if self._messages is not None:
            first, second = self._messages
            if first.id == second.id or any(
                message.id in self._store._messages for message in self._messages
            ):
                raise ConflictError("message_conflict", "Message already exists")


class InMemoryStore:
    """A process-local store whose adapters share one coherent set of dictionaries."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._users_by_email: dict[str, UUID] = {}
        self._users_by_username: dict[str, UUID] = {}
        self._tokens: dict[str, AuthToken] = {}
        self._sessions: dict[UUID, ChatSession] = {}
        self._messages: dict[UUID, ChatMessage] = {}
        self._user_locks: dict[UUID, asyncio.Lock] = {}
        self._session_locks: dict[UUID, asyncio.Lock] = {}
        self.users = InMemoryUserRepository(self)
        self.tokens = InMemoryTokenRepository(self)
        self.sessions = InMemorySessionRepository(self)
        self.messages = InMemoryMessageRepository(self)

    def session_lock(self, session_id: UUID) -> asyncio.Lock:
        lock = self._session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._session_locks[session_id] = lock
        return lock

    def user_lock(self, user_id: UUID) -> asyncio.Lock:
        lock = self._user_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._user_locks[user_id] = lock
        return lock

    def chat_uow(self) -> InMemoryChatUnitOfWork:
        return InMemoryChatUnitOfWork(self)

    def _add_user(self, user: User) -> None:
        self._validate_new_user(user)
        email_key, username_key = self._identity_keys(user)
        self._users[user.id] = user
        self._users_by_email[email_key] = user.id
        self._users_by_username[username_key] = user.id

    def _validate_new_user(self, user: User) -> None:
        email_key, username_key = self._identity_keys(user)
        if user.id in self._users:
            raise ConflictError("user_conflict", "User already exists")
        if email_key in self._users_by_email:
            raise ConflictError("email_conflict", "Email already exists")
        if username_key in self._users_by_username:
            raise ConflictError("username_conflict", "Username already exists")

    def _validate_user_replacement(self, user: User) -> None:
        current = self._users.get(user.id)
        if current is None:
            raise ConflictError("user_not_found", "User does not exist")
        email_key, username_key = self._identity_keys(user)
        email_owner = self._users_by_email.get(email_key)
        username_owner = self._users_by_username.get(username_key)
        if email_owner not in (None, user.id):
            raise ConflictError("email_conflict", "Email already exists")
        if username_owner not in (None, user.id):
            raise ConflictError("username_conflict", "Username already exists")
        if self._identity_keys(current) != (email_key, username_key):
            raise ValueError("staged user identity cannot change")

    @staticmethod
    def _identity_keys(user: User) -> tuple[str, str]:
        return user.email.strip().lower(), user.username.casefold()

    def _replace_user(self, user: User) -> None:
        self._users[user.id] = user

    def _add_message(self, message: ChatMessage) -> None:
        if message.id in self._messages:
            raise ConflictError("message_conflict", "Message already exists")
        self._messages[message.id] = message
