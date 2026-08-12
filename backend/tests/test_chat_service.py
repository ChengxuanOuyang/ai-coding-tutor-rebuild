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
