def test_backend_app_package_imports() -> None:
    import backend.app

    assert backend.app.__name__ == "backend.app"


def test_ai_package_imports() -> None:
    import backend.app.ai

    assert backend.app.ai.__name__ == "backend.app.ai"


def test_fastapi_app_modules_import() -> None:
    import backend.app.config
    import backend.app.main

    assert backend.app.config.__name__ == "backend.app.config"
    assert backend.app.main.__name__ == "backend.app.main"
