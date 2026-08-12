from backend.app.ai.provider import TutorRequest, TutorResponse


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


class MockTutorProvider:
    provider_name = "mock"
    model_name = "deterministic-tutor-v1"

    async def generate(self, request: TutorRequest) -> TutorResponse:
        content = (
            "Focus on the loop condition: which value must change for it to become false? "
            "Trace that value for the first three iterations before changing the code."
        )
        return TutorResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            input_tokens=_estimate_tokens(request.system_prompt + " " + request.user_message),
            output_tokens=_estimate_tokens(content),
        )
