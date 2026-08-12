# Task 7 Report — Problem Analyzer Boundary

## Scope

- Added immutable `AnalyzerRequest` and async `ProblemAnalyzer` protocol.
- Added deterministic, offline `MockProblemAnalyzer` returning the existing domain
  `ProblemAssessment`.
- Added contract tests for determinism, immutability, independent keyword dimensions,
  Chinese keywords, ASCII word boundaries, normalization, newest-history comparison, and
  blank/punctuation behavior.

## Deliberate Boundary Decisions

- `recent_messages` contains only user questions in oldest-to-newest order. The last tuple
  item is the only candidate for `same_problem` comparison.
- Normalization is Unicode NFKC, case folding, trimming, and whitespace collapse. Only
  non-empty exact normalized equality yields `same_problem=True`.
- The approved Task 7 material does not define an `is_elaboration` rule. The mock always
  returns `False` instead of claiming semantic understanding from keyword heuristics.
- Programming and maths keywords independently produce difficulty 3; no match produces 1.
  No network, API key, randomness, or Task 8 provider behavior was introduced.

## TDD Evidence

- RED: `.venv/bin/python -m pytest backend/tests/test_analyzer.py -v` collected 6 tests;
  all failed only with `ModuleNotFoundError: backend.app.ai.analyzer`.
- GREEN: focused analyzer + pedagogy tests passed (25 tests).

## Verification

- `.venv/bin/python -m pytest -v` — 84 passed.
- `.venv/bin/python -m ruff check backend` — passed.
- `git diff --check` — no output.
- Targeted sensitive-pattern scan — no matches.

The test environment emits one pre-existing FastAPI/httpx deprecation warning.
