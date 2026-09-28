"""PIN hash (bcrypt) + JWT üretim/doğrulama (HS256, python-jose)."""
from __future__ import annotations

import time
from typing import Any

import bcrypt
from jose import jwt

from ..api.settings import settings

ALG = "HS256"


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode(), pin_hash.encode())
    except ValueError:  # bozuk hash -> doğrulama başarısız
        return False


def make_token(claims: dict[str, Any]) -> str:
    now = int(time.time())
    payload = {**claims, "iat": now, "exp": now + settings.JWT_TTL_S}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALG)


def decode_token(token: str) -> dict[str, Any]:
    """Geçersiz/süresi dolmuş token'da JWTError yükseltir."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALG])
