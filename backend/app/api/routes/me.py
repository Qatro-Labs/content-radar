from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth import CurrentUser, require_user

router = APIRouter(prefix="/me", tags=["auth"])


@router.get("", response_model=CurrentUser)
def read_me(user: Annotated[CurrentUser, Depends(require_user)]) -> CurrentUser:
    """Usuario del token de Supabase. 401 sin un token válido, esté o no activo AUTH_REQUIRED."""
    return user
