import argparse
import asyncio
import json

from backend.app.ai.mock_provider import MockTutorProvider
from backend.app.ai.pedagogy import compute_hint_levels
from backend.app.ai.prompt_builder import PromptContext, build_system_prompt
from backend.app.ai.provider import TutorRequest
from backend.app.ai.types import StudentState


def _level(value: str) -> float:
    parsed = float(value)
    if not 1.0 <= parsed <= 5.0:
        raise argparse.ArgumentTypeError("level must be between 1 and 5")
    return parsed


def _difficulty(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 5:
        raise argparse.ArgumentTypeError("difficulty must be between 1 and 5")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic AI Tutor prototype.")
    parser.add_argument("--message", required=True)
    parser.add_argument("--programming-level", type=_level, required=True)
    parser.add_argument("--maths-level", type=_level, required=True)
    parser.add_argument("--programming-difficulty", type=_difficulty, required=True)
    parser.add_argument("--maths-difficulty", type=_difficulty, required=True)
    parser.add_argument("--same-problem", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> None:
    initial_state = StudentState(
        effective_programming_level=args.programming_level,
        effective_maths_level=args.maths_level,
    )
    programming_hint, maths_hint = compute_hint_levels(
        programming_difficulty=args.programming_difficulty,
        maths_difficulty=args.maths_difficulty,
        state=initial_state,
        same_problem=args.same_problem,
    )
    active_state = StudentState(
        effective_programming_level=args.programming_level,
        effective_maths_level=args.maths_level,
        programming_hint_level=programming_hint,
        maths_hint_level=maths_hint,
    )
    system_prompt = build_system_prompt(
        state=active_state,
        context=PromptContext(user_message=args.message),
    )
    response = await MockTutorProvider().generate(
        TutorRequest(system_prompt=system_prompt, user_message=args.message)
    )
    print(
        json.dumps(
            {
                "programming_hint_level": programming_hint.value,
                "maths_hint_level": maths_hint.value,
                "provider": response.provider,
                "model": response.model,
                "content": response.content,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
