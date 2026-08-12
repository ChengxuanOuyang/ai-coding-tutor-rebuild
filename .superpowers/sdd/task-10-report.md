# Task 10 Report: Atomic Tutoring Chat API

## Scope

Adds the protected `POST /sessions/{session_id}/messages` endpoint for the already-atomic
`ChatService.send_message()` operation. The endpoint is intentionally an HTTP projection; it does not change
Tutor/Analyzer orchestration, persistence, retry behaviour, provider selection, or OpenAI configuration.

## Contract implemented

- `MessageCreate` accepts only a strict `content` string, strips surrounding whitespace, and requires 1--4,000
  resulting characters. Unknown body fields are rejected.
- A successful `201` response contains only `session_id`, `user_message`, and `assistant_message`.
- The user message has no provider/model fields at all. The assistant message adds only provider/model; neither
  response exposes assessment, hints, effective levels, token counts, or the system prompt.
- Non-owner and unknown sessions return the same `404 session_not_found` response. Bad UUIDs and request data use
  the existing safe `422 validation_error` response.
- Invalid upstream contracts map to 502; unavailable upstreams map to 503. An unanticipated exception maps to
  `500 internal_error` without its exception text.

## TDD evidence

- RED: the new six API cases returned 405 because the POST route did not yet exist; the OpenAPI operation also had
  no `post` entry.
- GREEN: all six tests pass after the router, public schemas, error mappings, and isolated fixtures were added.
- The upstream 502 and 503 tests retrieve message history after the failed request and assert it remains empty,
  verifying no partial HTTP-visible turn was committed.

## Fixture isolation

`client_with_failing_tutor` has its own injected in-memory container. `logged_in_session` creates its account,
Bearer token, and session through the exact client used by the requesting test, so the failure path cannot
accidentally exercise a separate normal container.

## Verification

- Focused API regression: `.venv/bin/python -m pytest backend/tests/test_chat_api.py backend/tests/test_sessions_api.py
  backend/tests/test_auth_api.py -v` — `17 passed`.
- Full offline suite: `.venv/bin/python -m pytest backend/tests -v -m 'not openai_live'` — `121 passed`
  (one existing Starlette/httpx deprecation warning).
- Static checks: `.venv/bin/python -m ruff check .` — `All checks passed!`; `git diff --check` — no output.
- OpenAPI assertion verified the POST operation's `ChatTurnResponse` 201 schema and 422/500/502/503 responses.
- Sensitive-pattern scan across Task 10 files found no `sk-`, private-key, or AWS-access-key patterns.

This report contains no independent-review conclusion.
