from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.app.api.dependencies import AppContainer, get_container, get_current_user
from backend.app.api.schemas import (
    CreateSessionRequest,
    ErrorResponse,
    MessageResponse,
    SessionResponse,
    ValidationErrorResponse,
)
from backend.app.domain.models import User

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ValidationErrorResponse}},
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: CreateSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> SessionResponse:
    return await container.chat_service.create_session(user_id=current_user.id, title=request.title)


@router.get("", response_model=list[SessionResponse], responses={401: {"model": ErrorResponse}})
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[SessionResponse]:
    return await container.chat_service.list_sessions(user_id=current_user.id)


@router.get(
    "/{session_id}/messages",
    response_model=list[MessageResponse],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ValidationErrorResponse},
    },
)
async def list_messages(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[MessageResponse]:
    return await container.chat_service.list_messages(
        user_id=current_user.id,
        session_id=session_id,
    )
