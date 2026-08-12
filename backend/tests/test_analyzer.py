from dataclasses import FrozenInstanceError

import pytest


@pytest.mark.asyncio
async def test_mock_analyzer_is_deterministic_and_first_turn_is_new() -> None:
    from backend.app.ai.analyzer import AnalyzerRequest
    from backend.app.ai.mock_analyzer import MockProblemAnalyzer

    analyzer = MockProblemAnalyzer()
    request = AnalyzerRequest(user_message="Why does my loop not stop?", recent_messages=())

    first = await analyzer.analyze(request)
    second = await analyzer.analyze(request)

    assert first == second
    assert first.same_problem is False
    assert first.is_elaboration is False
    assert 1 <= first.programming_difficulty <= 5
    assert 1 <= first.maths_difficulty <= 5


def test_analyzer_request_is_immutable() -> None:
    from backend.app.ai.analyzer import AnalyzerRequest

    request = AnalyzerRequest(user_message="help", recent_messages=())

    with pytest.raises(FrozenInstanceError):
        request.user_message = "other"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_mock_analyzer_classifies_programming_and_maths_independently() -> None:
    from backend.app.ai.analyzer import AnalyzerRequest
    from backend.app.ai.mock_analyzer import MockProblemAnalyzer

    analyzer = MockProblemAnalyzer()

    programming = await analyzer.analyze(
        AnalyzerRequest(user_message="My Python while loop raises an error", recent_messages=())
    )
    maths = await analyzer.analyze(
        AnalyzerRequest(user_message="Solve this calculus equation", recent_messages=())
    )
    both = await analyzer.analyze(
        AnalyzerRequest(user_message="Use a loop to calculate an integral", recent_messages=())
    )

    assert (programming.programming_difficulty, programming.maths_difficulty) == (3, 1)
    assert (maths.programming_difficulty, maths.maths_difficulty) == (1, 3)
    assert (both.programming_difficulty, both.maths_difficulty) == (3, 3)


@pytest.mark.asyncio
async def test_mock_analyzer_supports_chinese_keywords_and_ascii_word_boundaries() -> None:
    from backend.app.ai.analyzer import AnalyzerRequest
    from backend.app.ai.mock_analyzer import MockProblemAnalyzer

    analyzer = MockProblemAnalyzer()
    chinese = await analyzer.analyze(
        AnalyzerRequest(user_message="这个循环里的方程为什么不对？", recent_messages=())
    )
    unrelated = await analyzer.analyze(
        AnalyzerRequest(user_message="The scallop is tasty.", recent_messages=())
    )

    assert (chinese.programming_difficulty, chinese.maths_difficulty) == (3, 3)
    assert (unrelated.programming_difficulty, unrelated.maths_difficulty) == (1, 1)


@pytest.mark.asyncio
async def test_mock_analyzer_compares_only_normalized_most_recent_user_problem() -> None:
    from backend.app.ai.analyzer import AnalyzerRequest
    from backend.app.ai.mock_analyzer import MockProblemAnalyzer

    result = await MockProblemAnalyzer().analyze(
        AnalyzerRequest(
            user_message="  WHY does my LOOP not stop?  ",
            recent_messages=("Why does my loop not stop?", "A different question"),
        )
    )
    same = await MockProblemAnalyzer().analyze(
        AnalyzerRequest(
            user_message="  WHY does my LOOP not stop?  ",
            recent_messages=("A different question", "why does my loop not stop?"),
        )
    )

    assert result.same_problem is False
    assert same.same_problem is True
    assert same.is_elaboration is False


@pytest.mark.asyncio
async def test_mock_analyzer_handles_blank_and_punctuation_only_messages_explicitly() -> None:
    from backend.app.ai.analyzer import AnalyzerRequest
    from backend.app.ai.mock_analyzer import MockProblemAnalyzer

    analyzer = MockProblemAnalyzer()
    blank = await analyzer.analyze(AnalyzerRequest(user_message="  ", recent_messages=(" ",)))
    punctuation = await analyzer.analyze(
        AnalyzerRequest(user_message="!!!", recent_messages=("!!!",))
    )

    assert blank.same_problem is False
    assert punctuation.same_problem is True
