from fastapi import FastAPI

from backend.app.api.auth import router as auth_router
from backend.app.api.dependencies import AppContainer, create_default_container
from backend.app.api.errors import install_error_handlers
from backend.app.api.users import router as users_router


def create_app(*, container: AppContainer | None = None) -> FastAPI:
    app = FastAPI()
    app.state.container = create_default_container() if container is None else container
    install_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(users_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
