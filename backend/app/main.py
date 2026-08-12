from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from backend.app.api.auth import router as auth_router
from backend.app.api.dependencies import AppContainer, create_default_container
from backend.app.api.errors import install_error_handlers
from backend.app.api.sessions import router as sessions_router
from backend.app.api.users import router as users_router


class _GlobalCORSFastAPI(FastAPI):
    """Keep CORS outside ServerErrorMiddleware so unexpected 500 responses are covered."""

    def __init__(self, *, cors_origins: tuple[str, ...]) -> None:
        super().__init__()
        self._cors_origins = cors_origins

    def build_middleware_stack(self) -> ASGIApp:
        app = super().build_middleware_stack()
        if not self._cors_origins:
            return app
        return CORSMiddleware(
            app=app,
            allow_origins=self._cors_origins,
            allow_methods=("*",),
            allow_headers=("*",),
        )


def create_app(
    *,
    container: AppContainer | None = None,
    cors_origins: tuple[str, ...] = (),
) -> FastAPI:
    app = _GlobalCORSFastAPI(cors_origins=cors_origins)
    app.state.container = create_default_container() if container is None else container
    install_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(sessions_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
