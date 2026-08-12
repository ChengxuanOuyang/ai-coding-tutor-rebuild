# Task 4 Report: In-Memory Authentication Core

Status: RE-REVIEW PENDING
Date: 2026-08-12
Worktree: `/Users/harrisonrio/Documents/下载常见工具/ai-coding-tutor-rebuild/.worktrees/phase-02a-fastapi-memory`

## Delivered

- `pwdlib` recommended password hashing and verification helpers.
- Cryptographically random bearer-token creation, SHA-256 digesting, and constant-time digest comparison.
- `AuthService` registration, login, authentication, and current-token logout with injected UTC clock, TTL,
  and token factory.
- Digest-only persistence; the plaintext token exists only in the login result.
- Deterministic coverage for credential-error equivalence, expiry deletion, null/unknown tokens, targeted
  logout, and repository uniqueness conflicts.

## TDD Evidence

- RED: `backend.app.services` did not exist while loading the new AuthService tests.
- GREEN: the focused AuthService and repository suites passed after the smallest security/service implementation.

## Final Verification

- Focused AuthService and repository tests: `22 passed` after the formal-review correction.
- Full suite: `66 passed, 1 warning`; the warning is the pre-existing FastAPI/Starlette TestClient deprecation.
- `ruff check backend`: `All checks passed!`.
- `git diff --check`: clean.
- Sensitive-pattern scan of Task 4 source, tests, prompt archive, and report: no matches for OpenAI-style
  keys, private keys, or AWS access keys.

## Formal Review Correction

The first formal Task 4 review is **FAIL**. The previous `Independent Review` PASS statement was written before
that formal review and was inaccurate; it has been removed.

1. **Important — credential timing enumeration:** `login()` short-circuited when the email was unknown, so it
   skipped the Argon2 verification performed by the wrong-password path. The repair adds a module-initialized
   dummy password hash and always performs exactly one password verification before raising the same safe error.
2. **Important — audit accuracy:** the report claimed a successful independent review before the formal review
   occurred. This record now preserves the actual sequence.

The deterministic RED test and code repair have been added. Formal re-review remains pending; do not interpret
this report as a re-review pass.
