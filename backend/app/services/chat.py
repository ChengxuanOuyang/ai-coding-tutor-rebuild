import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from html import escape
from uuid import UUID, uuid4

from backend.app.ai.analyzer import AnalyzerRequest, ProblemAnalyzer
from backend.app.ai.pedagogy import (
    coerce_pedagogy_metadata,
    compute_hint_levels,
    update_effective_level,
)
from backend.app.ai.prompt_builder import PromptContext, build_system_prompt
from backend.app.ai.provider import TutorProvider, TutorRequest, TutorResponse
from backend.app.ai.types import PedagogyMetadata, StudentState
from backend.app.domain.errors import NotFoundError, UpstreamInvalidResponseError
from backend.app.domain.models import (
    ChatMessage,
    ChatSession,
    MessageRole,
    ProblemAssessment,
)
from backend.app.repositories import (
    ChatUnitOfWork,
    MessageRepository,
    SessionRepository,
    UserRepository,
)

MAX_STUDENT_MESSAGE_CHARS = 4_000
MAX_RECENT_MESSAGES = 10
MAX_RECENT_CONTENT_CHARS = 4_000
TRUNCATED_HISTORY_MARKER = "[truncated]\n"


@dataclass(frozen=True)
class ChatTurn:
    """The two student-visible messages created by one committed tutoring turn."""

    user_message: ChatMessage
    assistant_message: ChatMessage


@dataclass(frozen=True)
class RecentHistory:
    """A selected message suffix and its independently bounded prompt serialization."""

    messages: tuple[ChatMessage, ...]
    serialized: str


class ChatService:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        messages: MessageRepository,
        analyzer: ProblemAnalyzer,
        tutor: TutorProvider,
        chat_uow_factory: Callable[[], ChatUnitOfWork],
        user_lock_factory: Callable[[UUID], asyncio.Lock],
        session_lock_factory: Callable[[UUID], asyncio.Lock],
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._messages = messages
        self._analyzer = analyzer
        self._tutor = tutor
        self._chat_uow_factory = chat_uow_factory
        self._user_lock_factory = user_lock_factory
        self._session_lock_factory = session_lock_factory
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)
        self._id_factory = id_factory

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

    async def send_message(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        content: str,
    ) -> ChatTurn:
        normalized_content = self._normalize_student_content(content)
        # All turns acquire locks in this order.  A user can own many sessions, so the
        # user lock protects the shared EMA state while the session lock protects its
        # history and preserves the no-TOCTOU ownership check.
        async with self._user_lock_factory(user_id):
            async with self._session_lock_factory(session_id):
                session = await self._sessions.get_for_user(session_id, user_id)
                if session is None:
                    raise self._session_not_found()

                history = await self._recent_history(session.id)
                assessment = await self._analyzer.analyze(
                    AnalyzerRequest(
                        user_message=normalized_content,
                        recent_messages=tuple(
                            message.content
                            for message in history.messages
                            if message.role is MessageRole.USER
                        ),
                    )
                )
                metadata = self._coerce_assessment(
                    assessment,
                    has_previous_exchange=bool(history.messages),
                )

                user = await self._users.get(user_id)
                if user is None:
                    raise self._session_not_found()
                state = StudentState(
                    effective_programming_level=user.effective_programming_level,
                    effective_maths_level=user.effective_maths_level,
                    programming_hint_level=user.programming_hint_level,
                    maths_hint_level=user.maths_hint_level,
                )
                programming_hint, maths_hint = compute_hint_levels(
                    programming_difficulty=metadata.programming_difficulty,
                    maths_difficulty=metadata.maths_difficulty,
                    state=state,
                    same_problem=metadata.same_problem,
                )
                updated_state = StudentState(
                    effective_programming_level=update_effective_level(
                        current_level=state.effective_programming_level,
                        difficulty=metadata.programming_difficulty,
                        final_hint_level=programming_hint,
                    ),
                    effective_maths_level=update_effective_level(
                        current_level=state.effective_maths_level,
                        difficulty=metadata.maths_difficulty,
                        final_hint_level=maths_hint,
                    ),
                    programming_hint_level=programming_hint,
                    maths_hint_level=maths_hint,
                )
                prompt = build_system_prompt(
                    state=updated_state,
                    context=PromptContext(
                        user_message=normalized_content,
                        recent_messages=history.serialized,
                    ),
                )
                tutor_response = self._validate_tutor_response(
                    await self._tutor.generate(
                        TutorRequest(system_prompt=prompt, user_message=normalized_content)
                    )
                )

                user_created_at = self._now()
                if history.messages:
                    user_created_at = self._later_timestamp(
                        history.messages[-1].created_at,
                        user_created_at,
                    )
                assistant_created_at = self._later_timestamp(user_created_at, self._now())
                user_message = ChatMessage(
                    id=self._id_factory(),
                    session_id=session.id,
                    role=MessageRole.USER,
                    content=normalized_content,
                    created_at=user_created_at,
                    assessment=ProblemAssessment(
                        programming_difficulty=metadata.programming_difficulty,
                        maths_difficulty=metadata.maths_difficulty,
                        same_problem=metadata.same_problem,
                        is_elaboration=metadata.is_elaboration,
                    ),
                    programming_hint_level=programming_hint,
                    maths_hint_level=maths_hint,
                )
                assistant_message = ChatMessage(
                    id=self._id_factory(),
                    session_id=session.id,
                    role=MessageRole.ASSISTANT,
                    content=tutor_response.content,
                    created_at=assistant_created_at,
                    provider=tutor_response.provider,
                    model=tutor_response.model,
                    input_tokens=tutor_response.input_tokens,
                    output_tokens=tutor_response.output_tokens,
                )
                updated_user = replace(
                    user,
                    effective_programming_level=updated_state.effective_programming_level,
                    effective_maths_level=updated_state.effective_maths_level,
                    programming_hint_level=programming_hint,
                    maths_hint_level=maths_hint,
                    updated_at=assistant_created_at,
                )
                async with self._chat_uow_factory() as uow:
                    uow.stage_messages(user_message, assistant_message)
                    uow.stage_user(updated_user)
                    await uow.commit()

                return ChatTurn(user_message=user_message, assistant_message=assistant_message)

    @staticmethod
    def _normalize_title(title: str | None) -> str | None:
        if title is None:
            return None
        normalized = title.strip()
        if len(normalized) > 120:
            raise ValueError("session title must be at most 120 characters")
        return normalized or None

    @staticmethod
    def _normalize_student_content(content: str) -> str:
        if not isinstance(content, str):
            raise ValueError("student message must be a string")
        normalized = content.strip()
        if not 1 <= len(normalized) <= MAX_STUDENT_MESSAGE_CHARS:
            raise ValueError("student message must contain 1 to 4,000 characters")
        return normalized

    async def _recent_history(self, session_id: UUID) -> RecentHistory:
        history = await self._messages.list_for_session(session_id)
        selected_reversed: list[tuple[ChatMessage, str]] = []
        serialized_chars = 0
        for message in reversed(history[-MAX_RECENT_MESSAGES:]):
            serialized_message = self._serialize_message(message)
            separator_chars = 1 if selected_reversed else 0
            fits_budget = (
                serialized_chars
                + separator_chars
                + self._prompt_serialized_length(serialized_message)
                <= MAX_RECENT_CONTENT_CHARS
            )
            if fits_budget:
                selected_reversed.append((message, serialized_message))
                serialized_chars += separator_chars + self._prompt_serialized_length(
                    serialized_message
                )
                continue
            if not selected_reversed:
                selected_reversed.append(
                    (message, self._truncate_newest_history_message(message))
                )
                break
            break
        selected = list(reversed(selected_reversed))
        return RecentHistory(
            messages=tuple(message for message, _ in selected),
            serialized="\n".join(serialized for _, serialized in selected),
        )

    @staticmethod
    def _serialize_message(message: ChatMessage) -> str:
        return f"{message.role.value}: {message.content}"

    @staticmethod
    def _truncate_newest_history_message(message: ChatMessage) -> str:
        prefix = f"{message.role.value}: "
        fixed_prefix = prefix + TRUNCATED_HISTORY_MARKER
        low = 0
        high = len(message.content)
        while low < high:
            candidate_length = (low + high + 1) // 2
            candidate = fixed_prefix + message.content[-candidate_length:]
            if ChatService._prompt_serialized_length(candidate) <= MAX_RECENT_CONTENT_CHARS:
                low = candidate_length
            else:
                high = candidate_length - 1
        return fixed_prefix + message.content[-low:]

    @staticmethod
    def _prompt_serialized_length(value: str) -> int:
        """Mirror Prompt Builder escaping so its per-field truncation never runs."""

        return len(escape(value, quote=False))

    @staticmethod
    def _coerce_assessment(
        assessment: ProblemAssessment,
        *,
        has_previous_exchange: bool,
    ) -> PedagogyMetadata:
        if not isinstance(assessment, ProblemAssessment):
            raise UpstreamInvalidResponseError(
                "invalid_analyzer_response",
                "Problem analyzer returned an invalid assessment",
            )
        raw = {
            "programming_difficulty": assessment.programming_difficulty,
            "maths_difficulty": assessment.maths_difficulty,
            "same_problem": assessment.same_problem,
            "is_elaboration": assessment.is_elaboration,
        }
        if (
            isinstance(assessment.programming_difficulty, bool)
            or not isinstance(assessment.programming_difficulty, int)
            or not 1 <= assessment.programming_difficulty <= 5
            or isinstance(assessment.maths_difficulty, bool)
            or not isinstance(assessment.maths_difficulty, int)
            or not 1 <= assessment.maths_difficulty <= 5
            or not isinstance(assessment.same_problem, bool)
            or not isinstance(assessment.is_elaboration, bool)
        ):
            raise UpstreamInvalidResponseError(
                "invalid_analyzer_response",
                "Problem analyzer returned an invalid assessment",
            )
        try:
            return coerce_pedagogy_metadata(raw, has_previous_exchange=has_previous_exchange)
        except ValueError as exc:
            raise UpstreamInvalidResponseError(
                "invalid_analyzer_response",
                "Problem analyzer returned an invalid assessment",
            ) from exc

    @staticmethod
    def _later_timestamp(previous: datetime, candidate: datetime) -> datetime:
        if candidate <= previous:
            return previous + timedelta(microseconds=1)
        return candidate

    @staticmethod
    def _validate_tutor_response(response: object) -> TutorResponse:
        valid_strings = (
            isinstance(response, TutorResponse)
            and isinstance(response.content, str)
            and bool(response.content)
            and isinstance(response.provider, str)
            and bool(response.provider)
            and isinstance(response.model, str)
            and bool(response.model)
        )
        valid_tokens = (
            isinstance(response, TutorResponse)
            and not isinstance(response.input_tokens, bool)
            and isinstance(response.input_tokens, int)
            and response.input_tokens >= 0
            and not isinstance(response.output_tokens, bool)
            and isinstance(response.output_tokens, int)
            and response.output_tokens >= 0
        )
        if not valid_strings or not valid_tokens:
            raise UpstreamInvalidResponseError(
                "invalid_tutor_response",
                "Tutor returned an invalid response",
            )
        return response

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is not UTC:
            raise ValueError("clock must return aware UTC timestamps")
        return now

    @staticmethod
    def _session_not_found() -> NotFoundError:
        return NotFoundError("session_not_found", "Session not found")
