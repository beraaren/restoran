"""Kimlik yönetim endpoint'leri — hepsi require("admin.users") ile korumalı.

employees/roles CRUD + venues/terminals liste + terminal create.
PIN create/update'ta bcrypt'lenir; hash asla dışarı çıkmaz.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..domain.db import SessionLocal
from ..domain.identity import Employee, Role, Terminal, Venue
from ..domain.permissions import ADMIN_USERS, PERMISSIONS
from .deps import require
from .security import hash_pin

router = APIRouter(prefix="/admin/identity", tags=["identity-admin"])

Admin = Annotated[dict, Depends(require(ADMIN_USERS))]


def _get_db() -> Session:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


DbDep = Annotated[Session, Depends(_get_db)]


# --------------------------------------------------------------- şemalar
class EmployeeCreate(BaseModel):
    venue_id: str
    full_name: str = Field(min_length=2)
    pin: str = Field(min_length=4, max_length=12)
    card_code: str | None = None
    role_id: str


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    pin: str | None = Field(default=None, min_length=4, max_length=12)
    card_code: str | None = None
    role_id: str | None = None
    active: bool | None = None


class RoleCreate(BaseModel):
    venue_id: str
    name: str
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = None
    permissions: list[str] | None = None


class TerminalCreate(BaseModel):
    venue_id: str
    code: str
    kind: str = "pos"
    name: str = ""


# --------------------------------------------------------------- serileştirme
def _emp_dict(e: Employee) -> dict[str, Any]:
    return {"id": e.id, "venue_id": e.venue_id, "full_name": e.full_name,
            "card_code": e.card_code, "role_id": e.role_id,
            "role_name": e.role.name if e.role else None, "active": e.active,
            "created_at": e.created_at.isoformat() if e.created_at else None}


def _role_dict(r: Role) -> dict[str, Any]:
    return {"id": r.id, "venue_id": r.venue_id, "name": r.name,
            "permissions": r.permissions}


def _terminal_dict(t: Terminal) -> dict[str, Any]:
    return {"id": t.id, "venue_id": t.venue_id, "code": t.code,
            "kind": t.kind, "name": t.name}


def _venue_dict(v: Venue) -> dict[str, Any]:
    return {"id": v.id, "tenant_id": v.tenant_id, "name": v.name, "slug": v.slug,
            "address": v.address, "timezone": v.timezone}


def _validate_perms(permissions: list[str]) -> None:
    unknown = [p for p in permissions if p not in PERMISSIONS]
    if unknown:
        raise HTTPException(422, f"bilinmeyen yetkiler: {unknown}")


# --------------------------------------------------------------- venues / terminals (salt-okunur + create)
@router.get("/venues")
async def list_venues(db: DbDep, _claims: Admin):
    return [_venue_dict(v) for v in db.scalars(select(Venue).order_by(Venue.name))]


@router.get("/terminals")
async def list_terminals(db: DbDep, _claims: Admin,
                         venue_id: str | None = Query(None)):
    q = select(Terminal).order_by(Terminal.code)
    if venue_id:
        q = q.where(Terminal.venue_id == venue_id)
    return [_terminal_dict(t) for t in db.scalars(q)]


@router.post("/terminals", status_code=201)
async def create_terminal(body: TerminalCreate, db: DbDep, _claims: Admin):
    if body.kind not in Terminal.KINDS:
        raise HTTPException(422, f"kind {Terminal.KINDS} olmalı")
    if not db.get(Venue, body.venue_id):
        raise HTTPException(404, "venue yok")
    t = Terminal(**body.model_dump())
    db.add(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "bu kod venue'da zaten var") from None
    db.refresh(t)
    return _terminal_dict(t)


# --------------------------------------------------------------- employees CRUD
@router.get("/employees")
async def list_employees(db: DbDep, _claims: Admin,
                         venue_id: str | None = Query(None)):
    q = select(Employee).order_by(Employee.full_name)
    if venue_id:
        q = q.where(Employee.venue_id == venue_id)
    return [_emp_dict(e) for e in db.scalars(q)]


@router.post("/employees", status_code=201)
async def create_employee(body: EmployeeCreate, db: DbDep, _claims: Admin):
    if not db.get(Venue, body.venue_id):
        raise HTTPException(404, "venue yok")
    if not db.get(Role, body.role_id):
        raise HTTPException(404, "rol yok")
    e = Employee(venue_id=body.venue_id, full_name=body.full_name,
                 pin_hash=hash_pin(body.pin), card_code=body.card_code,
                 role_id=body.role_id)
    db.add(e)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "kart kodu bu venue'da zaten kullanımda") from None
    db.refresh(e)
    return _emp_dict(e)


@router.put("/employees/{employee_id}")
async def update_employee(employee_id: str, body: EmployeeUpdate,
                          db: DbDep, _claims: Admin):
    e = db.get(Employee, employee_id)
    if not e:
        raise HTTPException(404, "çalışan yok")
    data = body.model_dump(exclude_unset=True)
    if "role_id" in data and not db.get(Role, data["role_id"]):
        raise HTTPException(404, "rol yok")
    pin = data.pop("pin", None)
    for k, v in data.items():
        setattr(e, k, v)
    if pin:
        e.pin_hash = hash_pin(pin)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "kart kodu bu venue'da zaten kullanımda") from None
    db.refresh(e)
    return _emp_dict(e)


@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, db: DbDep, _claims: Admin):
    e = db.get(Employee, employee_id)
    if not e:
        raise HTTPException(404, "çalışan yok")
    db.delete(e)
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------- roles CRUD
@router.get("/roles")
async def list_roles(db: DbDep, _claims: Admin, venue_id: str | None = Query(None)):
    q = select(Role).order_by(Role.name)
    if venue_id:
        q = q.where(Role.venue_id == venue_id)
    return [_role_dict(r) for r in db.scalars(q)]


@router.post("/roles", status_code=201)
async def create_role(body: RoleCreate, db: DbDep, _claims: Admin):
    if not db.get(Venue, body.venue_id):
        raise HTTPException(404, "venue yok")
    _validate_perms(body.permissions)
    r = Role(**body.model_dump())
    db.add(r)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "rol adı bu venue'da zaten var") from None
    db.refresh(r)
    return _role_dict(r)


@router.put("/roles/{role_id}")
async def update_role(role_id: str, body: RoleUpdate, db: DbDep, _claims: Admin):
    r = db.get(Role, role_id)
    if not r:
        raise HTTPException(404, "rol yok")
    data = body.model_dump(exclude_unset=True)
    if "permissions" in data:
        _validate_perms(data["permissions"])
    for k, v in data.items():
        setattr(r, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "rol adı bu venue'da zaten var") from None
    db.refresh(r)
    return _role_dict(r)


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, db: DbDep, _claims: Admin):
    r = db.get(Role, role_id)
    if not r:
        raise HTTPException(404, "rol yok")
    if db.scalars(select(Employee).where(Employee.role_id == role_id)).first():
        raise HTTPException(409, "bu rolü kullanan çalışanlar var")
    db.delete(r)
    db.commit()
    return {"ok": True}
