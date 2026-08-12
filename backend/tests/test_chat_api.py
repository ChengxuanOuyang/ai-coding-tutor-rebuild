from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.ai.provider import TutorResponse
from backend.app.main import create_app


def test_chat_api_returns_visible_messages_without_hidden_state(client, logged_in_session) -> None:
    headers, session_id = logged_in_session

    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "  Why does my loop not stop?  "},
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert set(payload) == {"session_id", "user_message", "assistant_message"}
    assert payload["session_id"] == session_id
    assert payload["user_message"] == {
        "id": payload["user_message"]["id"],
        "role": "user",
        "content": "Why does my loop not stop?",
        "created_at": payload["user_message"]["created_at"],
    }
    assert payload["assistant_message"]["role"] == "assistant"
    assert set(payload["assistant_message"]) == {
        "id",
        "role",
        "content",
        "created_at",
        "provider",
        "model",
    }
    serialized = response.text
    for hidden in (
        "effective_",
        "hint_level",
        "assessment",
        "input_tokens",
        "output_tokens",
        "system_prompt",
    ):
        assert hidden not in serialized


def test_chat_rejects_invalid_request_and_unknown_or_foreign_session_without_leaking_ownership(
    client, logged_in_session, register_and_login
) -> None:
    headers, session_id = logged_in_session
    other_headers = register_and_login("other@example.com", "other")

    blank = client.post(
        f"/sessions/{session_id}/messages", json={"content": " \t "}, headers=headers
    )
    too_long = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "x" * 4_001},
        headers=headers,
    )
    extra = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "Help", "hint_level": 3},
        headers=headers,
    )
    invalid_uuid = client.post(
        "/sessions/not-a-uuid/messages", json={"content": "Help"}, headers=headers
    )
    foreign = client.post(
        f"/sessions/{session_id}/messages", json={"content": "Help"}, headers=other_headers
    )
    unknown = client.post(
        f"/sessions/{uuid4()}/messages", json={"content": "Help"}, headers=other_headers
    )

    assert [response.status_code for response in (blank, too_long, extra, invalid_uuid)] == [
        422,
        422,
        422,
        422,
    ]
    assert all(response.json()["error"]["code"] == "validation_error" for response in (
        blank,
        too_long,
        extra,
        invalid_uuid,
    ))
    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json()["error"] == unknown.json()["error"] == {
        "code": "session_not_found",
        "message": "Session not found",
    }


def test_invalid_upstream_response_maps_to_bad_gateway_without_a_partial_turn(
    client, logged_in_session, monkeypatch
) -> None:
    headers, session_id = logged_in_session

    async def invalid_response(_: object) -> TutorResponse:
        return TutorResponse("", "mock", "deterministic-tutor-v1", 0, 0)

    tutor = client.app.state.container.chat_service._tutor
    monkeypatch.setattr(tutor, "generate", invalid_response)

    response = client.post(
        f"/sessions/{session_id}/messages", json={"content": "Help"}, headers=headers
    )

    assert response.status_code == 502
    assert response.json()["error"] == {
        "code": "invalid_tutor_response",
        "message": "Tutor returned an invalid response",
    }
    history = client.get(f"/sessions/{session_id}/messages", headers=headers)
    assert history.status_code == 200
    assert history.json() == []


def test_upstream_failure_uses_stable_safe_error_and_leaves_no_partial_turn(
    client_with_failing_tutor, logged_in_session
) -> None:
    headers, session_id = logged_in_session

    response = client_with_failing_tutor.post(
        f"/sessions/{session_id}/messages", json={"content": "Help"}, headers=headers
    )

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "upstream_unavailable",
        "message": "Tutor unavailable",
    }
    history = client_with_failing_tutor.get(f"/sessions/{session_id}/messages", headers=headers)
    assert history.status_code == 200
    assert history.json() == []


def test_unexpected_error_has_a_safe_internal_response(
    client, logged_in_session, monkeypatch
) -> None:
    headers, session_id = logged_in_session

    async def unexpected_failure(**_: object) -> object:
        raise RuntimeError("provider secret: do-not-expose")

    monkeypatch.setattr(
        client.app.state.container.chat_service, "send_message", unexpected_failure
    )
    with TestClient(client.app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post(
            f"/sessions/{session_id}/messages", json={"content": "Help"}, headers=headers
        )

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"}
    }
    assert "do-not-expose" not in response.text


def test_global_cors_wraps_safe_500_and_preserves_standard_error_responses(
    client, logged_in_session, monkeypatch
) -> None:
    headers, session_id = logged_in_session
    origin = "https://frontend.example"
    app = create_app(
        container=client.app.state.container,
        cors_origins=(origin,),
    )

    async def unexpected_failure(**_: object) -> object:
        raise RuntimeError("provider secret: do-not-expose")

    monkeypatch.setattr(app.state.container.chat_service, "send_message", unexpected_failure)
    with TestClient(app, raise_server_exceptions=False) as cors_client:
        internal = cors_client.post(
            f"/sessions/{session_id}/messages",
            json={"content": "Help"},
            headers={**headers, "Origin": origin},
        )
        missing = cors_client.get("/not-found", headers={"Origin": origin})
        invalid = cors_client.post(
            f"/sessions/{session_id}/messages",
            json={"content": "  "},
            headers={**headers, "Origin": origin},
        )

    assert internal.status_code == 500
    assert internal.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"}
    }
    assert "do-not-expose" not in internal.text
    assert missing.status_code == 404
    assert invalid.status_code == 422
    assert [response.headers["access-control-allow-origin"] for response in (
        internal,
        missing,
        invalid,
    )] == [origin, origin, origin]


def test_failing_tutor_client_is_fully_isolated_from_the_default_client(
    client, client_with_failing_tutor, logged_in_session, register_and_login
) -> None:
    failing_headers, failing_session_id = logged_in_session
    normal_headers = register_and_login("student@example.com", "student")
    normal_session = client.post("/sessions", json={"title": "Normal"}, headers=normal_headers)

    assert normal_session.status_code == 201
    normal_turn = client.post(
        f"/sessions/{normal_session.json()['id']}/messages",
        json={"content": "Help"},
        headers=normal_headers,
    )
    failing_turn = client_with_failing_tutor.post(
        f"/sessions/{failing_session_id}/messages",
        json={"content": "Help"},
        headers=failing_headers,
    )
    normal_history = client.get(
        f"/sessions/{normal_session.json()['id']}/messages", headers=normal_headers
    )
    failing_history = client_with_failing_tutor.get(
        f"/sessions/{failing_session_id}/messages", headers=failing_headers
    )

    assert normal_turn.status_code == 201
    assert failing_turn.status_code == 503
    assert normal_history.status_code == failing_history.status_code == 200
    assert len(normal_history.json()) == 2
    assert failing_history.json() == []


def test_chat_operation_is_documented_in_openapi(client) -> None:
    operation = client.get("/openapi.json").json()["paths"]["/sessions/{session_id}/messages"][
        "post"
    ]

    assert operation["responses"]["201"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ChatTurnResponse")
    assert {"422", "502", "503", "500"} <= set(operation["responses"])
