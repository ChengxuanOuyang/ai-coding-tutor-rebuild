# Task 9 Report: Atomic Tutoring Turns

## Outcome

`ChatService.send_message()` now serializes each session's full tutoring turn and commits exactly two
messages plus the updated User state through the existing atomic in-memory Unit of Work.

## Contract implemented

- Validates normalized student content (1-4,000 characters) before any model call.
- Holds the session-specific lock for ownership, history, Analyzer, pedagogy, Prompt, Tutor and commit.
- Budgets history as a contiguous suffix of at most 10 messages and 4,000 content characters, then restores
  chronological order. Analyzer receives only the historic user messages, never the current message.
- Treats the Analyzer output as untrusted: requires the `ProblemAssessment` type, exact flag types, and integer
  difficulties from 1 through 5 before applying Phase 01 coercion and pedagogy.
- Uses Phase 01 independent hint computation and EMA updates; stores the assessment and hints on the internal
  user message, and provider/model/token accounting on the assistant message.
- Does not call retry logic in this orchestration layer. The approved Task 9 flow has no retry step; adapter-specific
  transient retry remains a later integration concern.
- Injects UUID and clock factories. A fixed clock still produces a chronological pair and preserves complete turn
  ordering in the repository.

## TDD evidence

- Initial RED: the new service tests collected 11 cases, all failing because `ChatService` lacked the Task 9
  orchestration dependencies and operation.
- Additional RED: with a fixed clock and deliberately reverse UUIDs, the second turn sorted before the first.
  The service now advances a new turn past the latest history timestamp before constructing its two messages.
- GREEN focused regression: `36 passed` for Chat Service, pedagogy and Prompt Builder.
- Final verification: `100 passed`; `ruff check .` reported `All checks passed!`; `git diff --check` was clean.

## Scope note

The default application container and shared API test container now pass the same in-memory User repository,
session lock, UOW, Mock Analyzer and Mock Tutor to `ChatService`. This is wiring required to preserve the existing
application factory behavior after the service constructor gained the Task 9 dependencies. No chat HTTP endpoint
or public response schema was added; those remain Task 10 work.
