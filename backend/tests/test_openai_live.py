import os

import openai
import pytest

from backend.app.ai.analyzer import AnalyzerRequest
from backend.app.ai.openai_adapters import OpenAIProblemAnalyzer, OpenAITutorProvider
from backend.app.ai.provider import TutorRequest
from backend.app.config import Settings

pytestmark = pytest.mark.openai_live


@pytest.fixture(scope="module")
def live_settings(request: pytest.FixtureRequest) -> Settings:
    if request.config.option.markexpr.strip() != "openai_live":
        pytest.skip("requires explicit selection with -m openai_live")
    if os.getenv("APP_PROVIDER_MODE", "").strip().lower() != "openai":
        pytest.skip("requires APP_PROVIDER_MODE=openai")
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("requires OPENAI_API_KEY")
    return Settings.from_env()


@pytest.fixture(scope="module")
def live_client(live_settings: Settings) -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(
        api_key=live_settings.openai_api_key,
        timeout=live_settings.openai_timeout_seconds,
        max_retries=0,
    )


@pytest.mark.asyncio
async def test_openai_analyzer_live(
    live_client: openai.AsyncOpenAI, live_settings: Settings
) -> None:
    analyzer = OpenAIProblemAnalyzer(
        client=live_client,
        model=live_settings.analyzer_model,
        reasoning_effort=live_settings.reasoning_effort,
        timeout_seconds=live_settings.openai_timeout_seconds,
    )

    result = await analyzer.analyze(
        AnalyzerRequest(
            user_message="Why does this Python loop never stop?",
            recent_messages=(),
        )
    )

    assert 1 <= result.programming_difficulty <= 5
    assert 1 <= result.maths_difficulty <= 5
    assert isinstance(result.same_problem, bool)
    assert isinstance(result.is_elaboration, bool)


@pytest.mark.asyncio
async def test_openai_tutor_live(
    live_client: openai.AsyncOpenAI, live_settings: Settings
) -> None:
    provider = OpenAITutorProvider(
        client=live_client,
        model=live_settings.tutor_model,
        reasoning_effort=live_settings.reasoning_effort,
        timeout_seconds=live_settings.openai_timeout_seconds,
    )

    result = await provider.generate(
        TutorRequest(
            system_prompt="Give one brief Socratic hint. Do not provide a full solution.",
            user_message="Why does while True keep running?",
        )
    )

    assert result.provider == "openai"
    assert result.model == live_settings.tutor_model
    assert result.content
    assert result.input_tokens > 0
    assert result.output_tokens > 0
