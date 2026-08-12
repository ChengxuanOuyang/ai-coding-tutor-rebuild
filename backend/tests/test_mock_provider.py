import pytest


@pytest.mark.asyncio
async def test_mock_provider_returns_deterministic_response() -> None:
    from backend.app.ai.mock_provider import MockTutorProvider
    from backend.app.ai.provider import TutorRequest, TutorResponse

    provider = MockTutorProvider()
    request = TutorRequest(
        system_prompt="Programming hint level: 2/5",
        user_message="Why does the loop continue?",
    )

    first = await provider.generate(request)
    second = await provider.generate(request)

    assert first == second
    assert isinstance(first, TutorResponse)
    assert first.provider == "mock"
    assert first.model == "deterministic-tutor-v1"
    assert first.input_tokens > 0
    assert first.output_tokens > 0
    assert "condition" in first.content.lower()


@pytest.mark.asyncio
async def test_mock_provider_does_not_require_network_or_credentials() -> None:
    from backend.app.ai.mock_provider import MockTutorProvider
    from backend.app.ai.provider import TutorRequest

    response = await MockTutorProvider().generate(
        TutorRequest(system_prompt="", user_message=""),
    )

    assert response.provider == "mock"
    assert response.input_tokens == 1
    assert response.content
