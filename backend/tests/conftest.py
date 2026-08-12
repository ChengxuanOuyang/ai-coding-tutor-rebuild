from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.ai.mock_analyzer import MockProblemAnalyzer
from backend.app.ai.mock_provider import MockTutorProvider
from backend.app.ai.provider import TutorRequest, TutorResponse
from backend.app.api.dependencies import AppContainer
from backend.app.domain.errors import UpstreamUnavailableError
from backend.app.domain.models import User
from backend.app.main import create_app
from backend.app.memory import InMemoryStore
from backend.app.services.auth import AuthService
from backend.app.services.chat import ChatService


class FailingTutor:
    async def generate(self, _: TutorRequest) -> TutorResponse:
        raise UpstreamUnavailableError("upstream_unavailable", "Tutor unavailable")


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


@pytest.fixture
def user_factory(fixed_now: datetime) -> Callable[..., User]:
    def build(**overrides: object) -> User:
        values: dict[str, object] = {
            "email": "student@example.com",
            "username": "student",
            "password_hash": "argon2-hash",
            "self_programming_level": 2,
            "self_maths_level": 3,
            "now": fixed_now,
        }
        values.update(overrides)
        return User.create(**values)  # type: ignore[arg-type]

    return build


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def auth_service(store: InMemoryStore, fixed_now: datetime) -> AuthService:
    return AuthService(
        users=store.users,
        tokens=store.tokens,
        clock=lambda: fixed_now,
        token_ttl=86_400,
    )


@pytest.fixture
def client(auth_service: AuthService, store: InMemoryStore) -> TestClient:
    return TestClient(
        create_app(
            container=AppContainer(
                auth_service=auth_service,
                chat_service=ChatService(
                    users=store.users,
                    sessions=store.sessions,
                    messages=store.messages,
                    analyzer=MockProblemAnalyzer(),
                    tutor=MockTutorProvider(),
                    chat_uow_factory=store.chat_uow,
                    user_lock_factory=store.user_lock,
                    session_lock_factory=store.session_lock,
                ),
            )
        )
    )


@pytest.fixture
def client_with_failing_tutor(auth_service: AuthService, store: InMemoryStore) -> TestClient:
    """An independent app container whose Tutor always fails upstream."""
    return TestClient(
        create_app(
            container=AppContainer(
                auth_service=auth_service,
                chat_service=ChatService(
                    users=store.users,
                    sessions=store.sessions,
                    messages=store.messages,
                    analyzer=MockProblemAnalyzer(),
                    tutor=FailingTutor(),
                    chat_uow_factory=store.chat_uow,
                    user_lock_factory=store.user_lock,
                    session_lock_factory=store.session_lock,
                ),
            )
        )
    )


@pytest.fixture
def register_and_login(client: TestClient) -> Callable[[str, str], dict[str, str]]:
    def register(email: str, username: str) -> dict[str, str]:
        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "username": username,
                "password": "correct horse battery",
                "self_programming_level": 2,
                "self_maths_level": 3,
            },
        )
        assert response.status_code == 201
        login = client.post(
            "/auth/login",
            json={"email": email, "password": "correct horse battery"},
        )
        assert login.status_code == 200
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return register


@pytest.fixture
def logged_in_session(request: pytest.FixtureRequest) -> tuple[dict[str, str], str]:
    """Create the session inside the exact container selected by the requesting test."""
    client_name = (
        "client_with_failing_tutor"
        if "client_with_failing_tutor" in request.fixturenames
        else "client"
    )
    api_client: TestClient = request.getfixturevalue(client_name)
    headers = _register_and_login(api_client, "student@example.com", "student")
    created = api_client.post("/sessions", json={"title": "Loops"}, headers=headers)
    assert created.status_code == 201
    return headers, created.json()["id"]


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
