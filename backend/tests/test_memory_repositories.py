from asyncio import Lock
from dataclasses import replace
from datetime import timedelta
from inspect import iscoroutinefunction
from uuid import UUID, uuid4

import pytest

from backend.app.domain.models import AuthToken, ChatMessage, ChatSession, MessageRole


def test_repository_protocols_import_and_expose_async_contracts() -> None:
    from backend.app.repositories import (
        ChatUnitOfWork,
        MessageRepository,
        SessionRepository,
        TokenRepository,
        UserRepository,
    )

    for protocol, method in (
        (UserRepository, "add"),
        (TokenRepository, "get_by_digest"),
        (SessionRepository, "get_for_user"),
        (MessageRepository, "list_for_session"),
        (ChatUnitOfWork, "commit"),
    ):
        assert hasattr(protocol, method)
        assert iscoroutinefunction(getattr(protocol, method))


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
async def test_user_repository_normalizes_indexes_for_replaced_identity_fields(
    user_factory,
) -> None:
    from backend.app.domain.errors import ConflictError
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    malformed_email = replace(
        user_factory(),
        email=" Student@EXAMPLE.com ",
        username="Student",
        username_key="not-the-real-key",
    )
    await store.users.add(malformed_email)

    assert await store.users.get_by_email("student@example.com") == malformed_email
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
async def test_session_and_message_repository_sort_equal_timestamps_by_uuid(
    user_factory,
    fixed_now,
) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    await store.users.add(user)
    lower_session_id = UUID("00000000-0000-0000-0000-000000000001")
    higher_session_id = UUID("00000000-0000-0000-0000-000000000002")
    lower_session = ChatSession(lower_session_id, user.id, "Lower", fixed_now, fixed_now)
    higher_session = ChatSession(higher_session_id, user.id, "Higher", fixed_now, fixed_now)
    await store.sessions.add(higher_session)
    await store.sessions.add(lower_session)

    lower_message_id = UUID("00000000-0000-0000-0000-000000000003")
    higher_message_id = UUID("00000000-0000-0000-0000-000000000004")
    lower_message = ChatMessage(
        lower_message_id, lower_session.id, MessageRole.USER, "Lower", fixed_now
    )
    higher_message = ChatMessage(
        higher_message_id, lower_session.id, MessageRole.ASSISTANT, "Higher", fixed_now
    )
    await store.messages.add(higher_message)
    await store.messages.add(lower_message)

    assert await store.sessions.list_for_user(user.id) == [lower_session, higher_session]
    assert await store.messages.list_for_session(lower_session.id) == [
        lower_message,
        higher_message,
    ]


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
    user_message = ChatMessage(
        UUID("00000000-0000-0000-0000-000000000007"),
        session.id,
        MessageRole.USER,
        "Help",
        fixed_now,
    )
    assistant_message = ChatMessage(
        UUID("00000000-0000-0000-0000-000000000008"),
        session.id,
        MessageRole.ASSISTANT,
        "Try this",
        fixed_now,
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
    user_message = ChatMessage(
        UUID("00000000-0000-0000-0000-000000000009"),
        session.id,
        MessageRole.USER,
        "Help",
        fixed_now,
    )
    assistant_message = ChatMessage(
        UUID("00000000-0000-0000-0000-000000000010"),
        session.id,
        MessageRole.ASSISTANT,
        "Try this",
        fixed_now,
    )
    changed = replace(user, effective_programming_level=3.0)

    async with store.chat_uow() as uow:
        uow.stage_user(changed)
        uow.stage_messages(user_message, assistant_message)
        await uow.commit()

    assert await store.users.get(user.id) == changed
    assert await store.messages.list_for_session(session.id) == [user_message, assistant_message]


@pytest.mark.asyncio
async def test_chat_uow_rejects_user_only_commit_without_visible_change(user_factory) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    await store.users.add(user)

    async with store.chat_uow() as uow:
        uow.stage_user(replace(user, effective_programming_level=4.0))
        with pytest.raises(ValueError, match="requires a staged user and message pair"):
            await uow.commit()

    assert await store.users.get(user.id) == user


@pytest.mark.asyncio
async def test_chat_uow_rejects_messages_only_commit_without_visible_change(
    user_factory,
    fixed_now,
) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    session = ChatSession(uuid4(), user.id, None, fixed_now, fixed_now)
    user_message = ChatMessage(uuid4(), session.id, MessageRole.USER, "Help", fixed_now)
    assistant_message = ChatMessage(
        uuid4(), session.id, MessageRole.ASSISTANT, "Try this", fixed_now
    )

    async with store.chat_uow() as uow:
        uow.stage_messages(user_message, assistant_message)
        with pytest.raises(ValueError, match="requires a staged user and message pair"):
            await uow.commit()

    assert await store.messages.list_for_session(session.id) == []


def test_chat_uow_requires_user_assistant_pair_for_one_session(fixed_now) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    first_session_id = uuid4()
    user_message = ChatMessage(uuid4(), first_session_id, MessageRole.USER, "Help", fixed_now)
    assistant_message = ChatMessage(
        uuid4(), first_session_id, MessageRole.ASSISTANT, "Try this", fixed_now
    )
    other_assistant_message = ChatMessage(
        uuid4(), uuid4(), MessageRole.ASSISTANT, "Other", fixed_now
    )
    uow = store.chat_uow()

    with pytest.raises(ValueError, match="user and assistant pair"):
        uow.stage_messages(assistant_message, user_message)
    with pytest.raises(ValueError, match="same session"):
        uow.stage_messages(user_message, other_assistant_message)


@pytest.mark.asyncio
async def test_session_lock_is_reused_for_the_same_uuid() -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    session_id = uuid4()

    assert store.session_lock(session_id) is store.session_lock(session_id)
    assert store.session_lock(session_id) is not store.session_lock(uuid4())


@pytest.mark.asyncio
async def test_user_lock_is_reused_for_the_same_uuid() -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user_id = uuid4()

    assert isinstance(store.user_lock(user_id), Lock)
    assert store.user_lock(user_id) is store.user_lock(user_id)
    assert store.user_lock(user_id) is not store.user_lock(uuid4())
