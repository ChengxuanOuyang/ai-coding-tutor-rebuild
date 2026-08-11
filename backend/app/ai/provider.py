from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TutorRequest:
    system_prompt: str
    user_message: str


@dataclass(frozen=True)
class TutorResponse:
    content: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


class TutorProvider(Protocol):
    def generate(self, request: TutorRequest) -> TutorResponse: ...
