def test_register_login_me_logout_flow(client) -> None:
    register = client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "username": "student",
            "password": "correct horse battery",
            "self_programming_level": 2,
            "self_maths_level": 4,
        },
    )

    assert register.status_code == 201
    assert "password_hash" not in register.text
    assert "effective_programming_level" not in register.text

    login = client.post(
        "/auth/login",
        json={"email": "student@example.com", "password": "correct horse battery"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["self_maths_level"] == 4

    logout = client.post("/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert logout.content == b""

    rejected = client.get("/users/me", headers=headers)
    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "invalid_token"


def test_authentication_failures_have_safe_uniform_responses(client) -> None:
    missing = client.get("/users/me")
    malformed = client.get("/users/me", headers={"Authorization": "Basic abc"})
    unknown = client.get("/users/me", headers={"Authorization": "Bearer unknown-token"})

    responses = [missing, malformed, unknown]
    assert [response.status_code for response in responses] == [401, 401, 401]
    assert [response.json()["error"]["code"] for response in responses] == [
        "invalid_token",
        "invalid_token",
        "invalid_token",
    ]
    assert [response.headers["www-authenticate"] for response in responses] == [
        "Bearer",
        "Bearer",
        "Bearer",
    ]


def test_registration_validation_conflict_and_clients_are_isolated(client) -> None:
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    first_client = TestClient(create_app())
    second_client = TestClient(create_app())
    payload = {
        "email": "student@example.com",
        "username": "student",
        "password": "correct horse battery",
        "self_programming_level": 2,
        "self_maths_level": 4,
    }

    assert first_client.post("/auth/register", json=payload).status_code == 201
    assert first_client.post("/auth/register", json=payload).status_code == 409
    assert second_client.post("/auth/register", json=payload).status_code == 201

    invalid = second_client.post(
        "/auth/register",
        json={**payload, "password": "do-not-echo-this-password", "self_programming_level": 2.0},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert "do-not-echo-this-password" not in invalid.text
    assert "Traceback" not in invalid.text

    conflict = first_client.post("/auth/register", json=payload)
    assert conflict.json()["error"]["code"] == "email_conflict"


def test_openapi_exposes_authentication_contract(client) -> None:
    schema = client.get("/openapi.json").json()

    assert {"/auth/register", "/auth/login", "/auth/logout", "/users/me"} <= set(
        schema["paths"]
    )
    assert "RegisterRequest" in schema["components"]["schemas"]
    assert "LoginResponse" in schema["components"]["schemas"]
