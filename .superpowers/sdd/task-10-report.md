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

## First review remediation (re-review pending)

The first Task 10 review found the following two issues. This section records the deterministic reproductions and
minimal repairs; it is not an independent re-review result.

- **P1 — CORS omitted from safe 500:** FastAPI's `ServerErrorMiddleware` is outside ordinary user middleware, so a
  usual `app.add_middleware(CORSMiddleware, ...)` configuration cannot attach CORS headers to an Exception-handler
  500. RED supplied an explicit permitted Origin and raised a secret-bearing `RuntimeError`; no CORS configuration
  boundary existed yet. `_GlobalCORSFastAPI` now wraps FastAPI's fully built middleware stack in `CORSMiddleware`,
  placing CORS around `ServerErrorMiddleware` while retaining the returned FastAPI object's state, OpenAPI endpoint,
  and TestClient interface. Origins are explicit `create_app(cors_origins=...)` input, default to disabled, and are
  never hard-coded in an error handler. GREEN verifies matching CORS headers on the safe 500, framework 404, and
  request-validation 422 without leaking the RuntimeError detail.
- **P2 — failure-client state sharing:** `client_with_failing_tutor` previously depended on the regular Store and
  AuthService fixtures. RED used both clients with the same credentials; normal-client registration returned 409,
  proving shared state. The failing fixture now creates its own `InMemoryStore`, `AuthService`, `ChatService`, and
  `AppContainer`. GREEN proves the normal client independently commits its two-message turn while the failing client
  returns 503 and has no messages.

Re-review remains pending.

## Remediation verification

- RED: `.venv/bin/python -m pytest backend/tests/test_chat_api.py -k 'global_cors or fully_isolated' -v` — both
  deterministic regressions failed before production changes: missing `cors_origins` configuration and a `409` from
  the normal client caused by shared state.
- Focused GREEN: `.venv/bin/python -m pytest backend/tests/test_chat_api.py -v` — `8 passed`.
- Full offline suite: `.venv/bin/python -m pytest backend/tests -v -m 'not openai_live'` — `123 passed`
  (one existing Starlette/httpx deprecation warning).
- `.venv/bin/python -m ruff check .` — `All checks passed!`; `git diff --check` — no output; changed-file sensitive
  pattern scan found no `sk-`, private-key, or AWS access-key patterns.
