import asyncio
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from backend.app.ai.analyzer import AnalyzerRequest
from backend.app.ai.provider import TutorRequest, TutorResponse
from backend.app.domain.errors import (
    ConflictError,
    NotFoundError,
    UpstreamInvalidResponseError,
    UpstreamUnavailableError,
)
from backend.app.domain.models import (
    ChatMessage,
    ChatSession,
    MessageRole,
    ProblemAssessment,
    User,
)
from backend.app.memory import InMemoryStore
from backend.app.services.chat import ChatService


class RecordingAnalyzer:
    def __init__(self, assessment: ProblemAssessment | object) -> None:
        self.assessment = assessment
        self.requests: list[AnalyzerRequest] = []

    async def analyze(self, request: AnalyzerRequest) -> ProblemAssessment:
        self.requests.append(request)
        return self.assessment  # type: ignore[return-value]


class FailingAnalyzer:
    async def analyze(self, request: AnalyzerRequest) -> ProblemAssessment:
        raise UpstreamUnavailableError("analyzer_unavailable", "Analyzer unavailable")


class RecordingTutor:
    def __init__(self) -> None:
        self.requests: list[TutorRequest] = []

    async def generate(self, request: TutorRequest) -> TutorResponse:
        self.requests.append(request)
        return TutorResponse("Guidance", "test", "test-model", 11, 7)


class FailingTutor:
    async def generate(self, request: TutorRequest) -> TutorResponse:
        raise UpstreamUnavailableError("tutor_unavailable", "Tutor unavailable")


class FixedTutor:
    def __init__(self, response: object) -> None:
        self.response = response

    async def generate(self, request: TutorRequest) -> TutorResponse:
        return self.response  # type: ignore[return-value]


class SteppingClock:
    def __init__(self, start: datetime) -> None:
        self._next = start

    def __call__(self) -> datetime:
        result = self._next
        self._next += timedelta(microseconds=1)
        return result


@pytest.fixture
async def chat_setup() -> tuple[InMemoryStore, User, ChatSession, SteppingClock]:
    now = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
    store = InMemoryStore()
    user = User.create(
        email="student@example.com",
        username="student",
        password_hash="argon2-hash",
        self_programming_level=2,
        self_maths_level=3,
        now=now,
    )
    session = ChatSession(uuid4(), user.id, None, now, now)
    await store.users.add(user)
    await store.sessions.add(session)
    return store, user, session, SteppingClock(now + timedelta(seconds=1))


def make_service(
    *,
    store: InMemoryStore,
    clock: Callable[[], datetime],
    analyzer: object,
    tutor: object,
    id_factory: Callable[[], UUID] = uuid4,
) -> ChatService:
    return ChatService(
        users=store.users,
        sessions=store.sessions,
        messages=store.messages,
        analyzer=analyzer,  # type: ignore[arg-type]
        tutor=tutor,  # type: ignore[arg-type]
        chat_uow_factory=store.chat_uow,
        user_lock_factory=store.user_lock,
        session_lock_factory=store.session_lock,
        clock=clock,
        id_factory=id_factory,
    )


@pytest.mark.asyncio
async def test_send_message_commits_auditable_messages_and_updated_state(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, clock = chat_setup
    analyzer = RecordingAnalyzer(ProblemAssessment(3, 1, False, False))
    tutor = RecordingTutor()
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=tutor)

    turn = await service.send_message(
        user_id=user.id,
        session_id=session.id,
        content="  Why does my loop not stop?  ",
    )

    history = await store.messages.list_for_session(session.id)
    updated_user = await store.users.get(user.id)
    assert history == [turn.user_message, turn.assistant_message]
    assert turn.user_message.content == "Why does my loop not stop?"
    assert turn.user_message.assessment == ProblemAssessment(3, 1, False, False)
    assert turn.user_message.programming_hint_level.value == 2
    assert turn.user_message.maths_hint_level.value == 1
    assert turn.user_message.created_at < turn.assistant_message.created_at
    assert turn.assistant_message.provider == "test"
    assert turn.assistant_message.model == "test-model"
    assert (turn.assistant_message.input_tokens, turn.assistant_message.output_tokens) == (11, 7)
    assert updated_user is not None
    assert updated_user.effective_programming_level == pytest.approx(2.08)
    assert updated_user.effective_maths_level == pytest.approx(2.8666666666666667)
    assert updated_user.programming_hint_level.value == 2
    assert updated_user.maths_hint_level.value == 1
    assert analyzer.requests == [
        AnalyzerRequest(user_message="Why does my loop not stop?", recent_messages=())
    ]
    assert "<untrusted_user_message>\nWhy does my loop not stop?" in tutor.requests[0].system_prompt


@pytest.mark.asyncio
async def test_send_message_uses_a_contiguous_recent_history_suffix_and_user_only_analysis_history(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, clock = chat_setup
    base = datetime(2026, 8, 12, 10, 0, tzinfo=UTC)
    messages = (
        ChatMessage(uuid4(), session.id, MessageRole.USER, "a" * 1_500, base),
        ChatMessage(
            uuid4(),
            session.id,
            MessageRole.ASSISTANT,
            "b" * 1_500,
            base + timedelta(seconds=1),
        ),
        ChatMessage(
            uuid4(),
            session.id,
            MessageRole.USER,
            "c" * 1_500,
            base + timedelta(seconds=2),
        ),
    )
    for message in messages:
        await store.messages.add(message)
    analyzer = RecordingAnalyzer(ProblemAssessment(1, 1, False, False))
    tutor = RecordingTutor()
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=tutor)

    await service.send_message(user_id=user.id, session_id=session.id, content="new question")

    assert analyzer.requests == [
        AnalyzerRequest(user_message="new question", recent_messages=("c" * 1_500,))
    ]
    prompt = tutor.requests[0].system_prompt
    assert "c" * 1_500 in prompt
    assert "b" * 1_500 in prompt
    assert "a" * 1_500 not in prompt


@pytest.mark.asyncio
async def test_history_budget_counts_serialization_and_keeps_the_newest_oversized_message_tail(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, clock = chat_setup
    newest_tail = "LATEST-HISTORY-SENTINEL"
    long_content = "x" * (4_000 - len(newest_tail)) + newest_tail
    await store.messages.add(
        ChatMessage(
            uuid4(),
            session.id,
            MessageRole.USER,
            long_content,
            datetime(2026, 8, 12, 10, 0, tzinfo=UTC),
        )
    )
    analyzer = RecordingAnalyzer(ProblemAssessment(1, 1, False, False))
    tutor = RecordingTutor()
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=tutor)

    await service.send_message(user_id=user.id, session_id=session.id, content="new question")

    recent = tutor.requests[0].system_prompt.split("<untrusted_recent_messages>\n", 1)[1].split(
        "\n</untrusted_recent_messages>", 1
    )[0]
    assert len(recent) <= 4_000
    assert newest_tail in recent
    assert recent.count("[truncated]") == 1
    assert analyzer.requests == [
        AnalyzerRequest(user_message="new question", recent_messages=(long_content,))
    ]


@pytest.mark.asyncio
async def test_history_budget_accounts_for_prompt_escaping_without_losing_the_newest_tail(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, clock = chat_setup
    newest_tail = "LATEST-ESCAPED-SENTINEL"
    content = "<" * (3_994 - len(newest_tail)) + newest_tail
    await store.messages.add(
        ChatMessage(
            uuid4(),
            session.id,
            MessageRole.USER,
            content,
            datetime(2026, 8, 12, 10, 0, tzinfo=UTC),
        )
    )
    tutor = RecordingTutor()
    service = make_service(
        store=store,
        clock=clock,
        analyzer=RecordingAnalyzer(ProblemAssessment(1, 1, False, False)),
        tutor=tutor,
    )

    await service.send_message(user_id=user.id, session_id=session.id, content="new question")

    recent = tutor.requests[0].system_prompt.split("<untrusted_recent_messages>\n", 1)[1].split(
        "\n</untrusted_recent_messages>", 1
    )[0]
    assert len(recent) <= 4_000
    assert newest_tail in recent
    assert recent.count("[truncated]") == 1


@pytest.mark.asyncio
async def test_history_budget_counts_role_prefixes_and_separators_at_the_exact_boundary(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, clock = chat_setup
    old_content = "o" * 1_982
    newest_content = "n" * 1_994 + "LATEST"
    await store.messages.add(
        ChatMessage(
            uuid4(),
            session.id,
            MessageRole.USER,
            old_content,
            datetime(2026, 8, 12, 10, 0, tzinfo=UTC),
        )
    )
    await store.messages.add(
        ChatMessage(
            uuid4(),
            session.id,
            MessageRole.ASSISTANT,
            newest_content,
            datetime(2026, 8, 12, 10, 1, tzinfo=UTC),
        )
    )
    await store.messages.add(
        ChatMessage(
            uuid4(),
            session.id,
            MessageRole.USER,
            "oldest",
            datetime(2026, 8, 12, 9, 59, tzinfo=UTC),
        )
    )
    tutor = RecordingTutor()
    service = make_service(
        store=store,
        clock=clock,
        analyzer=RecordingAnalyzer(ProblemAssessment(1, 1, False, False)),
        tutor=tutor,
    )

    await service.send_message(user_id=user.id, session_id=session.id, content="new question")

    recent = tutor.requests[0].system_prompt.split("<untrusted_recent_messages>\n", 1)[1].split(
        "\n</untrusted_recent_messages>", 1
    )[0]
    assert len(recent) <= 4_000
    assert newest_content in recent
    assert old_content in recent
    assert "oldest" not in recent
    assert "[truncated]" not in recent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analyzer,tutor,error_type",
    [
        (FailingAnalyzer(), RecordingTutor(), UpstreamUnavailableError),
        (RecordingAnalyzer(object()), RecordingTutor(), UpstreamInvalidResponseError),
        (
            RecordingAnalyzer(ProblemAssessment(1, 1, False, False)),
            FailingTutor(),
            UpstreamUnavailableError,
        ),
    ],
)
async def test_analyzer_metadata_and_tutor_failures_leave_no_partial_turn_or_state_change(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
    analyzer: object,
    tutor: object,
    error_type: type[Exception],
) -> None:
    store, user, session, clock = chat_setup
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=tutor)
    before = await store.users.get(user.id)

    with pytest.raises(error_type):
        await service.send_message(user_id=user.id, session_id=session.id, content="Help")

    assert await store.messages.list_for_session(session.id) == []
    assert await store.users.get(user.id) == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        object(),
        TutorResponse("", "provider", "model", 0, 0),
        TutorResponse("answer", "", "model", 0, 0),
        TutorResponse("answer", "provider", "", 0, 0),
        TutorResponse("answer", "provider", "model", True, 0),
        TutorResponse("answer", "provider", "model", 0, True),
        TutorResponse("answer", "provider", "model", -1, 0),
        TutorResponse("answer", "provider", "model", 0, -1),
        TutorResponse("answer", "provider", "model", "1", 0),
    ],
)
async def test_invalid_tutor_response_leaves_no_partial_turn_or_state_change(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
    response: object,
) -> None:
    store, user, session, clock = chat_setup
    service = make_service(
        store=store,
        clock=clock,
        analyzer=RecordingAnalyzer(ProblemAssessment(1, 1, False, False)),
        tutor=FixedTutor(response),
    )
    before = await store.users.get(user.id)

    with pytest.raises(UpstreamInvalidResponseError) as error:
        await service.send_message(user_id=user.id, session_id=session.id, content="Help")

    assert (error.value.code, error.value.safe_message) == (
        "invalid_tutor_response",
        "Tutor returned an invalid response",
    )
    assert await store.messages.list_for_session(session.id) == []
    assert await store.users.get(user.id) == before


@pytest.mark.asyncio
async def test_prompt_failure_and_uow_failure_leave_no_partial_turn_or_state_change(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, user, session, clock = chat_setup
    analyzer = RecordingAnalyzer(ProblemAssessment(1, 1, False, False))
    tutor = RecordingTutor()
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=tutor)
    before = await store.users.get(user.id)

    def fail_prompt(**_: object) -> str:
        raise ValueError("prompt failure")

    monkeypatch.setattr("backend.app.services.chat.build_system_prompt", fail_prompt)
    with pytest.raises(ValueError, match="prompt failure"):
        await service.send_message(user_id=user.id, session_id=session.id, content="Help")
    assert await store.messages.list_for_session(session.id) == []
    assert await store.users.get(user.id) == before

    monkeypatch.undo()
    existing = ChatMessage(
        UUID("00000000-0000-0000-0000-000000000001"),
        session.id,
        MessageRole.USER,
        "existing",
        datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
    )
    await store.messages.add(existing)
    ids = iter((existing.id, UUID("00000000-0000-0000-0000-000000000002")))
    collision_service = make_service(
        store=store,
        clock=clock,
        analyzer=analyzer,
        tutor=tutor,
        id_factory=lambda: next(ids),
    )
    with pytest.raises(ConflictError, match="Message already exists"):
        await collision_service.send_message(user_id=user.id, session_id=session.id, content="Help")
    assert await store.messages.list_for_session(session.id) == [existing]
    assert await store.users.get(user.id) == before


@pytest.mark.asyncio
async def test_send_message_checks_session_ownership_inside_lock_before_model_calls(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, clock = chat_setup
    other = replace(
        user,
        id=uuid4(),
        email="other@example.com",
        username="other",
        username_key="other",
    )
    await store.users.add(other)
    analyzer = RecordingAnalyzer(ProblemAssessment(1, 1, False, False))
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=RecordingTutor())

    with pytest.raises(NotFoundError, match="Session not found"):
        await service.send_message(user_id=other.id, session_id=session.id, content="Help")

    assert analyzer.requests == []
    assert await store.messages.list_for_session(session.id) == []


@pytest.mark.asyncio
async def test_same_session_turns_are_serial_and_second_turn_observes_first_turn(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, clock = chat_setup
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    class BlockingAnalyzer(RecordingAnalyzer):
        async def analyze(self, request: AnalyzerRequest) -> ProblemAssessment:
            self.requests.append(request)
            if len(self.requests) == 1:
                first_started.set()
                await release_first.wait()
            return ProblemAssessment(1, 1, False, False)

    analyzer = BlockingAnalyzer(ProblemAssessment(1, 1, False, False))
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=RecordingTutor())
    first = asyncio.create_task(
        service.send_message(user_id=user.id, session_id=session.id, content="first question")
    )
    await first_started.wait()
    second = asyncio.create_task(
        service.send_message(user_id=user.id, session_id=session.id, content="second question")
    )
    await asyncio.sleep(0)
    assert len(analyzer.requests) == 1
    release_first.set()
    await asyncio.gather(first, second)

    assert analyzer.requests[1] == AnalyzerRequest(
        user_message="second question", recent_messages=("first question",)
    )
    assert [message.content for message in await store.messages.list_for_session(session.id)] == [
        "first question",
        "Guidance",
        "second question",
        "Guidance",
    ]


@pytest.mark.asyncio
async def test_same_user_different_sessions_do_not_lose_a_state_update(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, first_session, clock = chat_setup
    second_session = ChatSession(
        uuid4(),
        user.id,
        None,
        datetime(2026, 8, 12, 9, 1, tzinfo=UTC),
        datetime(2026, 8, 12, 9, 1, tzinfo=UTC),
    )
    await store.sessions.add(second_session)
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    second_started = asyncio.Event()

    class BlockingFirstTutor:
        calls = 0

        async def generate(self, request: TutorRequest) -> TutorResponse:
            self.calls += 1
            if self.calls == 1:
                first_started.set()
                await release_first.wait()
            else:
                second_started.set()
            return TutorResponse("Guidance", "test", "model", 1, 1)

    service = make_service(
        store=store,
        clock=clock,
        analyzer=RecordingAnalyzer(ProblemAssessment(3, 1, False, False)),
        tutor=BlockingFirstTutor(),
    )
    first = asyncio.create_task(
        service.send_message(user_id=user.id, session_id=first_session.id, content="first")
    )
    await first_started.wait()
    second = asyncio.create_task(
        service.send_message(user_id=user.id, session_id=second_session.id, content="second")
    )
    await asyncio.sleep(0)
    assert not second_started.is_set()
    release_first.set()
    await asyncio.gather(first, second)

    updated = await store.users.get(user.id)
    assert updated is not None
    assert updated.effective_programming_level == pytest.approx(2.144)


@pytest.mark.asyncio
async def test_different_users_do_not_block_each_others_sessions(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, first_user, first_session, clock = chat_setup
    second_user = replace(
        first_user,
        id=uuid4(),
        email="other@example.com",
        username="other",
        username_key="other",
    )
    second_session = ChatSession(
        uuid4(),
        second_user.id,
        None,
        datetime(2026, 8, 12, 9, 1, tzinfo=UTC),
        datetime(2026, 8, 12, 9, 1, tzinfo=UTC),
    )
    await store.users.add(second_user)
    await store.sessions.add(second_session)
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    second_finished = asyncio.Event()

    class BlockingFirstTutor:
        calls = 0

        async def generate(self, request: TutorRequest) -> TutorResponse:
            self.calls += 1
            if self.calls == 1:
                first_started.set()
                await release_first.wait()
            else:
                second_finished.set()
            return TutorResponse("Guidance", "test", "model", 1, 1)

    service = make_service(
        store=store,
        clock=clock,
        analyzer=RecordingAnalyzer(ProblemAssessment(1, 1, False, False)),
        tutor=BlockingFirstTutor(),
    )
    first = asyncio.create_task(
        service.send_message(user_id=first_user.id, session_id=first_session.id, content="first")
    )
    await first_started.wait()
    second = asyncio.create_task(
        service.send_message(user_id=second_user.id, session_id=second_session.id, content="second")
    )
    await asyncio.wait_for(second_finished.wait(), timeout=1)
    assert second.done()
    release_first.set()
    await first


@pytest.mark.asyncio
async def test_fixed_clock_keeps_complete_turns_in_creation_order(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock],
) -> None:
    store, user, session, _ = chat_setup
    ids = iter(
        (
            UUID("00000000-0000-0000-0000-000000000004"),
            UUID("00000000-0000-0000-0000-000000000003"),
            UUID("00000000-0000-0000-0000-000000000002"),
            UUID("00000000-0000-0000-0000-000000000001"),
        )
    )
    def fixed_clock() -> datetime:
        return datetime(2026, 8, 12, 11, 0, tzinfo=UTC)

    service = make_service(
        store=store,
        clock=fixed_clock,
        analyzer=RecordingAnalyzer(ProblemAssessment(1, 1, False, False)),
        tutor=RecordingTutor(),
        id_factory=lambda: next(ids),
    )

    await service.send_message(user_id=user.id, session_id=session.id, content="first")
    await service.send_message(user_id=user.id, session_id=session.id, content="second")

    assert [message.content for message in await store.messages.list_for_session(session.id)] == [
        "first",
        "Guidance",
        "second",
        "Guidance",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["", " \t\n ", "x" * 4_001])
async def test_send_message_enforces_normalized_student_content_limits(
    chat_setup: tuple[InMemoryStore, User, ChatSession, SteppingClock], content: str
) -> None:
    store, user, session, clock = chat_setup
    analyzer = RecordingAnalyzer(ProblemAssessment(1, 1, False, False))
    service = make_service(store=store, clock=clock, analyzer=analyzer, tutor=RecordingTutor())

    with pytest.raises(ValueError, match="student message"):
        await service.send_message(user_id=user.id, session_id=session.id, content=content)

    assert analyzer.requests == []
    assert await store.messages.list_for_session(session.id) == []
