"""GET /auth/me — token'daki claims'ı olduğu gibi döner (istemci yetkisini buradan okur)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from .deps import get_current_claims

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(claims: Annotated[dict, Depends(get_current_claims)]):
    return claims
