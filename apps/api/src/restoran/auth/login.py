"""POST /auth/login/pin — venue slug + çalışan id/kart + PIN ile giriş.

Hata sözleşmesi: venue/çalışan/bad PIN ayrımı gizlenir (401), pasif çalışan 403.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..api.settings import settings
from ..domain.db import SessionLocal
from ..domain.identity import Employee, Tenant, Terminal, Venue
from .security import make_token, verify_pin

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginPinBody(BaseModel):
    venue_slug: str
    employee_id_or_card: str = Field(min_length=1)
    pin: str = Field(min_length=4, max_length=12)
    terminal_id: str | None = None


def _get_db() -> Session:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


DbDep = Annotated[Session, Depends(_get_db)]


def _find_venue(db: DbDep, slug: str) -> Venue | None:
    # venue slug'ı doğrudan, tenant slug'ı üzerinden de yakalanır
    venue = db.scalar(select(Venue).where(Venue.slug == slug))
    if venue:
        return venue
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant:
        return db.scalar(select(Venue).where(Venue.tenant_id == tenant.id))
    return None


def _employee_dict(e: Employee) -> dict:
    return {
        "employee_id": e.id,
        "full_name": e.full_name,
        "card_code": e.card_code,
        "role": e.role.name,
        "permissions": e.role.permissions,
        "venue_id": e.venue_id,
        "active": e.active,
    }


def build_token_claims(e: Employee, terminal_id: str | None) -> dict:
    return {
        "sub": e.id,
        "venue_id": e.venue_id,
        "role": e.role.name,
        "perms": list(e.role.permissions or []),
        "terminal_id": terminal_id,
    }


@router.post("/login/pin")
async def login_pin(body: LoginPinBody, db: DbDep):
    venue = _find_venue(db, body.venue_slug)
    if not venue:
        raise HTTPException(401, "giriş başarısız")

    emp = db.scalar(select(Employee).where(
        Employee.venue_id == venue.id,
        or_(Employee.id == body.employee_id_or_card,
            Employee.card_code == body.employee_id_or_card)))
    if not emp or not verify_pin(body.pin, emp.pin_hash):
        raise HTTPException(401, "giriş başarısız")
    if not emp.active:
        raise HTTPException(403, "çalışan pasif")

    terminal_id = body.terminal_id
    if terminal_id:
        ok = db.scalar(select(Terminal).where(
            Terminal.id == terminal_id, Terminal.venue_id == venue.id))
        if not ok:
            raise HTTPException(422, "terminal bu mekana ait değil")

    token = make_token(build_token_claims(emp, terminal_id))
    return {"access_token": token, "token_type": "bearer",
            "expires_in": settings.JWT_TTL_S, "employee": _employee_dict(emp)}
