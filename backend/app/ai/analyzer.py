from dataclasses import dataclass
from typing import Protocol

from backend.app.domain.models import ProblemAssessment


@dataclass(frozen=True)
class AnalyzerRequest:
    """Untrusted student input and user-only history, ordered oldest to newest."""

    user_message: str
    recent_messages: tuple[str, ...]


class ProblemAnalyzer(Protocol):
    async def analyze(self, request: AnalyzerRequest) -> ProblemAssessment: ...
