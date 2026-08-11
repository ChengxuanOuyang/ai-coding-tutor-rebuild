def test_backend_app_package_imports() -> None:
    import backend.app

    assert backend.app.__name__ == "backend.app"


def test_ai_package_imports() -> None:
    import backend.app.ai

    assert backend.app.ai.__name__ == "backend.app.ai"
