from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from backend.app.domain.models import AuthToken, ChatMessage, ChatSession, MessageRole


@pytest.mark.asyncio
async def test_user_repository_enforces_normalized_email_and_username_uniqueness(
    user_factory,
) -> None:
    from backend.app.domain.errors import ConflictError
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    await store.users.add(user_factory(email=" Student@Example.com ", username="Student"))

    with pytest.raises(ConflictError, match="Email already exists"):
        await store.users.add(user_factory(email="student@example.com", username="other"))
    with pytest.raises(ConflictError, match="Username already exists"):
        await store.users.add(user_factory(email="other@example.com", username="student"))


@pytest.mark.asyncio
async def test_session_repository_returns_only_the_owners_sessions(user_factory, fixed_now) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    owner = user_factory()
    other = user_factory(email="other@example.com", username="other")
    await store.users.add(owner)
    await store.users.add(other)
    owned = ChatSession(uuid4(), owner.id, "Owned", fixed_now, fixed_now)
    foreign = ChatSession(uuid4(), other.id, "Foreign", fixed_now, fixed_now)
    await store.sessions.add(owned)
    await store.sessions.add(foreign)

    assert await store.sessions.get_for_user(owned.id, owner.id) == owned
    assert await store.sessions.get_for_user(foreign.id, owner.id) is None
    assert await store.sessions.list_for_user(owner.id) == [owned]


@pytest.mark.asyncio
async def test_message_repository_sorts_by_creation_time(user_factory, fixed_now) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    session = ChatSession(uuid4(), user.id, None, fixed_now, fixed_now)
    newer = ChatMessage(
        uuid4(), session.id, MessageRole.ASSISTANT, "Second", fixed_now + timedelta(seconds=1)
    )
    older = ChatMessage(uuid4(), session.id, MessageRole.USER, "First", fixed_now)
    await store.messages.add(newer)
    await store.messages.add(older)

    assert await store.messages.list_for_session(session.id) == [older, newer]


@pytest.mark.asyncio
async def test_token_lookup_and_expired_token_deletion(user_factory, fixed_now) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    token = AuthToken("digest", user.id, fixed_now - timedelta(days=1), fixed_now)
    await store.tokens.add(token)

    assert await store.tokens.get_by_digest("digest") == token
    await store.tokens.delete_expired(fixed_now)
    assert await store.tokens.get_by_digest("digest") is None


@pytest.mark.asyncio
async def test_chat_uow_discards_all_staged_changes_without_commit(user_factory, fixed_now) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    await store.users.add(user)
    session = ChatSession(uuid4(), user.id, None, fixed_now, fixed_now)
    user_message = ChatMessage(uuid4(), session.id, MessageRole.USER, "Help", fixed_now)
    assistant_message = ChatMessage(
        uuid4(), session.id, MessageRole.ASSISTANT, "Try this", fixed_now
    )
    changed = replace(user, effective_programming_level=4.0, effective_maths_level=4.0)

    async with store.chat_uow() as uow:
        uow.stage_user(changed)
        uow.stage_messages(user_message, assistant_message)

    assert await store.users.get(user.id) == user
    assert await store.messages.list_for_session(session.id) == []


@pytest.mark.asyncio
async def test_chat_uow_commits_user_and_both_messages_together(user_factory, fixed_now) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    await store.users.add(user)
    session = ChatSession(uuid4(), user.id, None, fixed_now, fixed_now)
    user_message = ChatMessage(uuid4(), session.id, MessageRole.USER, "Help", fixed_now)
    assistant_message = ChatMessage(
        uuid4(), session.id, MessageRole.ASSISTANT, "Try this", fixed_now
    )
    changed = replace(user, effective_programming_level=3.0)

    async with store.chat_uow() as uow:
        uow.stage_user(changed)
        uow.stage_messages(user_message, assistant_message)
        await uow.commit()

    assert await store.users.get(user.id) == changed
    assert await store.messages.list_for_session(session.id) == [user_message, assistant_message]


@pytest.mark.asyncio
async def test_session_lock_is_reused_for_the_same_uuid() -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    session_id = uuid4()

    assert store.session_lock(session_id) is store.session_lock(session_id)
    assert store.session_lock(session_id) is not store.session_lock(uuid4())
