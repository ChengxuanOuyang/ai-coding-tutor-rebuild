# Task 8 Report: Asynchronous Tutor Provider and Retry

## Scope

- Converted the `TutorProvider` Protocol and deterministic Mock implementation to async.
- Added generic `retry_once()` with a single, transient-only retry and injected sleep.
- Moved CLI orchestration into async `_run()` and preserved its Phase 01 JSON/argparse contract through
  `asyncio.run()` in `main()`.
- Did not implement Chat orchestration or an OpenAI adapter.

## TDD Evidence

- RED: `.venv/bin/python -m pytest backend/tests/test_mock_provider.py backend/tests/test_retry.py -v`
  collected six tests. Existing synchronous `generate()` failed with `TypeError` when awaited; retry tests
  failed only because `backend.app.ai.retry` did not exist.
- GREEN: the focused Provider/Retry/CLI suite passed with `8 passed`.

## Verification

- Full suite: `.venv/bin/python -m pytest -v` — `88 passed` (one existing Starlette/httpx deprecation warning).
- Lint: `.venv/bin/python -m ruff check backend` — `All checks passed!`.
- CLI command retained `programming_hint_level: 3`, `maths_hint_level: 1`, Provider `mock`, and model
  `deterministic-tutor-v1`.
- `git diff --check` and the scoped sensitive-pattern scan are run immediately before commit.

## Migration Decisions

- `retry_once()` catches `Exception`, not `BaseException`; cancellations therefore propagate without retry.
- Tests inject an async no-op sleeper, avoiding real waits. The production default remains
  `asyncio.sleep(0.25)`.
- A second operation failure is returned to the caller as the same exception object without wrapping.

## Concerns

- The full suite has a pre-existing Starlette/httpx deprecation warning; it does not fail tests.
