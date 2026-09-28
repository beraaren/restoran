"""Kimlik domain modelleri: Tenant > Venue > (Terminal, Employee, Role).

Kurallar: idler UUIDv7 (default=uuid7), saatler tz-aware UTC, para burada yok.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .ids import uuid7


def _uuid() -> str:
    return str(uuid7())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    venues: Mapped[list[Venue]] = relationship(back_populates="tenant")


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    address: Mapped[str] = mapped_column(String, nullable=False, default="")
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="Europe/Istanbul")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    tenant: Mapped[Tenant] = relationship(back_populates="venues")
    terminals: Mapped[list[Terminal]] = relationship(back_populates="venue")
    employees: Mapped[list[Employee]] = relationship(back_populates="venue")
    roles: Mapped[list[Role]] = relationship(back_populates="venue")

    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_venue_slug_per_tenant"),)


class Terminal(Base):
    __tablename__ = "terminals"

    KINDS = ("pos", "floor", "kds", "kiosk")

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    venue_id: Mapped[str] = mapped_column(
        String, ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="pos")  # pos|floor|kds|kiosk
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    venue: Mapped[Venue] = relationship(back_populates="terminals")

    __table_args__ = (UniqueConstraint("venue_id", "code", name="uq_terminal_code_per_venue"),)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    venue_id: Mapped[str] = mapped_column(
        String, ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    venue: Mapped[Venue] = relationship(back_populates="roles")
    employees: Mapped[list[Employee]] = relationship(back_populates="role")

    __table_args__ = (UniqueConstraint("venue_id", "name", name="uq_role_name_per_venue"),)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    venue_id: Mapped[str] = mapped_column(
        String, ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String, nullable=False)  # bcrypt
    card_code: Mapped[str | None] = mapped_column(String, nullable=True)
    role_id: Mapped[str] = mapped_column(
        String, ForeignKey("roles.id"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    venue: Mapped[Venue] = relationship(back_populates="employees")
    role: Mapped[Role] = relationship(back_populates="employees")

    # kart kodu boşsa unique ihlali olmasın => venue+card üzerinde partial-ish teklik
    __table_args__ = (UniqueConstraint("venue_id", "card_code", name="uq_employee_card_per_venue"),)
