from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.domain.models import ChatMessage, MessageRole, ProblemAssessment
from backend.app.main import create_app
from backend.app.memory import InMemoryStore


def test_sessions_are_private_and_ordered(
    client: TestClient, register_and_login
) -> None:
    first_headers = register_and_login("first@example.com", "first")
    second_headers = register_and_login("second@example.com", "second")

    first = client.post("/sessions", json={"title": "First"}, headers=first_headers)
    second = client.post("/sessions", json={"title": "Second"}, headers=first_headers)

    assert first.status_code == 201
    assert second.status_code == 201
    listed = client.get("/sessions", headers=first_headers)
    assert listed.status_code == 200
    assert [session["id"] for session in listed.json()] == [
        first.json()["id"],
        second.json()["id"],
    ]

    hidden = client.get(
        f"/sessions/{first.json()['id']}/messages", headers=second_headers
    )
    unknown = client.get(f"/sessions/{uuid4()}/messages", headers=second_headers)
    assert hidden.status_code == unknown.status_code == 404
    assert hidden.json()["error"] == unknown.json()["error"] == {
        "code": "session_not_found",
        "message": "Session not found",
    }


def test_session_titles_are_normalized_and_validated(
    client: TestClient, register_and_login
) -> None:
    headers = register_and_login("student@example.com", "student")

    blank = client.post("/sessions", json={"title": "   \t "}, headers=headers)
    trimmed = client.post("/sessions", json={"title": "  Loops  "}, headers=headers)
    maximum = client.post("/sessions", json={"title": "x" * 120}, headers=headers)
    too_long = client.post("/sessions", json={"title": "x" * 121}, headers=headers)
    unexpected = client.post(
        "/sessions", json={"title": None, "extra": "nope"}, headers=headers
    )

    assert blank.status_code == trimmed.status_code == maximum.status_code == 201
    assert blank.json()["title"] is None
    assert trimmed.json()["title"] == "Loops"
    assert maximum.json()["title"] == "x" * 120
    assert too_long.status_code == unexpected.status_code == 422
    assert too_long.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_message_history_is_owned_sorted_and_public(
    client: TestClient, register_and_login, store: InMemoryStore
) -> None:
    headers = register_and_login("student@example.com", "student")
    created = client.post("/sessions", json={"title": None}, headers=headers)
    session_id = UUID(created.json()["id"])
    base = datetime(2026, 8, 12, tzinfo=UTC)
    await store.messages.add(ChatMessage(
        uuid4(),
        session_id,
        MessageRole.ASSISTANT,
        "later",
        base + timedelta(seconds=1),
        provider="internal-provider",
        model="internal-model",
        input_tokens=11,
        output_tokens=22,
    ))
    await store.messages.add(ChatMessage(
        uuid4(),
        session_id,
        MessageRole.USER,
        "earlier",
        base,
        assessment=ProblemAssessment(2, 3, False, False),
    ))

    response = client.get(f"/sessions/{session_id}/messages", headers=headers)

    assert response.status_code == 200
    assert [message["content"] for message in response.json()] == ["earlier", "later"]
    assert set(response.json()[0]) == {"id", "session_id", "role", "content", "created_at"}


def test_empty_message_history_is_returned_for_owner(
    client: TestClient, register_and_login
) -> None:
    headers = register_and_login("student@example.com", "student")
    created = client.post("/sessions", json={}, headers=headers)

    response = client.get(f"/sessions/{created.json()['id']}/messages", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_sessions_are_isolated_between_default_app_instances() -> None:
    first = TestClient(create_app())
    second = TestClient(create_app())
    first_headers = _register_and_login(first, "student@example.com", "student")
    second_headers = _register_and_login(second, "student@example.com", "student")

    assert (
        first.post("/sessions", json={"title": "Only first"}, headers=first_headers).status_code
        == 201
    )
    assert second.get("/sessions", headers=second_headers).json() == []


def test_invalid_session_uuid_is_a_safe_validation_error(
    client: TestClient, register_and_login
) -> None:
    headers = register_and_login("student@example.com", "student")

    response = client.get("/sessions/not-a-uuid/messages", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def _register_and_login(client: TestClient, email: str, username: str) -> dict[str, str]:
    register = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "correct horse battery",
            "self_programming_level": 2,
            "self_maths_level": 3,
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "correct horse battery"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
