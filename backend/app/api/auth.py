from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.dependencies import (
    AppContainer,
    bearer_scheme,
    get_container,
    get_current_user,
)
from backend.app.api.schemas import (
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
    ValidationErrorResponse,
)
from backend.app.domain.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    responses={409: {"model": ErrorResponse}, 422: {"model": ValidationErrorResponse}},
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    container: Annotated[AppContainer, Depends(get_container)],
) -> User:
    return await container.auth_service.register(
        email=str(request.email),
        username=request.username,
        password=request.password,
        self_programming_level=request.self_programming_level,
        self_maths_level=request.self_maths_level,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ValidationErrorResponse}},
)
async def login(
    request: LoginRequest,
    container: Annotated[AppContainer, Depends(get_container)],
) -> LoginResponse:
    issued = await container.auth_service.login(email=str(request.email), password=request.password)
    return LoginResponse(
        access_token=issued.token,
        token_type="bearer",
        expires_at=issued.expires_at,
    )


@router.post(
    "/logout",
    responses={401: {"model": ErrorResponse}},
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    container: Annotated[AppContainer, Depends(get_container)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Response:
    del current_user
    token = None if credentials is None else credentials.credentials
    await container.auth_service.logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
