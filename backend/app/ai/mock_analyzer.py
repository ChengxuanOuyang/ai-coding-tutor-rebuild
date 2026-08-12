import re
import unicodedata

from backend.app.ai.analyzer import AnalyzerRequest
from backend.app.domain.models import ProblemAssessment

_ASCII_PROGRAMMING_KEYWORDS = (
    "bug",
    "code",
    "coding",
    "error",
    "exception",
    "for",
    "function",
    "loop",
    "program",
    "programming",
    "python",
    "syntax",
    "variable",
    "while",
)
_CHINESE_PROGRAMMING_KEYWORDS = (
    "代码",
    "函数",
    "循环",
    "报错",
    "异常",
    "语法",
    "程序",
    "编程",
    "变量",
    "错误",
)
_ASCII_MATHS_KEYWORDS = (
    "algebra",
    "calculus",
    "derivative",
    "equation",
    "integral",
    "math",
    "maths",
    "mathematics",
    "matrix",
    "vector",
)
_CHINESE_MATHS_KEYWORDS = ("代数", "导数", "微积分", "方程", "积分", "向量", "数学", "矩阵")


def _normalise(message: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", message).casefold().split())


def _contains_keyword(
    message: str, *, ascii_keywords: tuple[str, ...], chinese_keywords: tuple[str, ...]
) -> bool:
    contains_ascii = any(
        re.search(rf"\b{re.escape(keyword)}\b", message) for keyword in ascii_keywords
    )
    return contains_ascii or any(keyword in message for keyword in chinese_keywords)


class MockProblemAnalyzer:
    """Deterministic test double using only documented keyword and equality rules."""

    async def analyze(self, request: AnalyzerRequest) -> ProblemAssessment:
        current = _normalise(request.user_message)
        recent_problem = _normalise(request.recent_messages[-1]) if request.recent_messages else ""
        same_problem = bool(current) and current == recent_problem

        return ProblemAssessment(
            programming_difficulty=(
                3
                if _contains_keyword(
                    current,
                    ascii_keywords=_ASCII_PROGRAMMING_KEYWORDS,
                    chinese_keywords=_CHINESE_PROGRAMMING_KEYWORDS,
                )
                else 1
            ),
            maths_difficulty=(
                3
                if _contains_keyword(
                    current,
                    ascii_keywords=_ASCII_MATHS_KEYWORDS,
                    chinese_keywords=_CHINESE_MATHS_KEYWORDS,
                )
                else 1
            ),
            same_problem=same_problem,
            # The contract supplies no semantic elaboration signal.  This mock therefore
            # deliberately never claims an elaboration based on a text heuristic.
            is_elaboration=False,
        )
