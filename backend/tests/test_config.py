from fastapi.testclient import TestClient


def test_settings_default_to_mock_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("APP_PROVIDER_MODE", raising=False)

    from backend.app.config import Settings

    settings = Settings.from_env()
    assert settings.provider_mode == "mock"
    assert settings.analyzer_model == "gpt-5.6-luna"
    assert settings.tutor_model == "gpt-5.6-terra"
    assert settings.token_ttl_seconds == 86_400


def test_openai_mode_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_PROVIDER_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from backend.app.config import Settings

    try:
        Settings.from_env()
    except ValueError as exc:
        assert str(exc) == "OPENAI_API_KEY is required in openai mode"
    else:
        raise AssertionError("expected configuration error")


def test_health_endpoint_does_not_call_ai() -> None:
    from backend.app.main import create_app

    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
