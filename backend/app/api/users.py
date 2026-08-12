from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_current_user
from backend.app.api.schemas import ErrorResponse, UserResponse
from backend.app.domain.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse, responses={401: {"model": ErrorResponse}})
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
