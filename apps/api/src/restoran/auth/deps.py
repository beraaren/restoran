"""FastAPI dependency'leri: claims çözümü + yetki kapısı."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_claims(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, Any]:
    if creds is None:
        raise HTTPException(401, "Authorization: Bearer <token> gerekli")
    try:
        return decode_token(creds.credentials)
    except Exception:  # noqa: BLE001
        raise HTTPException(401, "token geçersiz veya süresi dolmuş") from None


def require(perm: str):
    """Yetki kontrolü üreten fabrika: claims.perms içinde yoksa 403."""

    def checker(claims: Annotated[dict, Depends(get_current_claims)]) -> dict:
        if perm not in (claims.get("perms") or []):
            raise HTTPException(403, f"yetki yok: {perm}")
        return claims

    return checker
