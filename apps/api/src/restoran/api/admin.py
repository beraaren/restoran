"""Restoran Yönetim Paneli (admin) — çekirdek SaaS verileri.

Ses kaydinde konuşulan "her restoranın ortak çekirdeği": ürün/menü, masa,
personel & vardiya, tedarikçi & fatura, stok sayımı. Monitoring (vision/POS
mutabakatı) bu çekirdeğin üzerine oturan denetim katmanıdır.

CRUD + baseline: fiyat/cost burada durur; reconcile anomallerinin ₺
karşılığı ürün fiyatından hesaplanır (mock'taki sabit 150₺ yerine gerçek).
"""
from __future__ import annotations

import uuid
from datetime import date as date_t
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..store.db import Base, SessionLocal

router = APIRouter(prefix="/admin", tags=["admin"])


# ------------------------------------------------------------------ modeller
class Product(Base):
    __tablename__ = "products"
    item_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:10])
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, default="ana")
    price_tl: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    cost_tl: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    unit: Mapped[str] = mapped_column(String, default="porsiyon")
    active: Mapped[bool] = mapped_column(default=True)


class DTable(Base):
    __tablename__ = "dtables"
    table_id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, default="")
    seats: Mapped[int] = mapped_column(default=4)
    zone_id: Mapped[str | None] = mapped_column(String, nullable=True)  # zone config eşleşmesi
    active: Mapped[bool] = mapped_column(default=True)


class Staff(Base):
    __tablename__ = "staff"
    staff_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:10])
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="garson")  # aşçı|garson|kasiyer|müdür
    pin: Mapped[str] = mapped_column(String, default="")
    active: Mapped[bool] = mapped_column(default=True)


class Shift(Base):
    __tablename__ = "shifts"
    shift_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:10])
    staff_id: Mapped[str] = mapped_column(String, index=True)
    day: Mapped[str] = mapped_column(String, index=True)  # ISO date
    start: Mapped[str] = mapped_column(String, default="09:00")
    end: Mapped[str] = mapped_column(String, default="18:00")


class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:10])
    name: Mapped[str] = mapped_column(String, nullable=False)
    contact: Mapped[str] = mapped_column(String, default="")
    active: Mapped[bool] = mapped_column(default=True)


class Invoice(Base):
    __tablename__ = "invoices"
    invoice_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:10])
    supplier_id: Mapped[str] = mapped_column(String, index=True)
    day: Mapped[str] = mapped_column(String, index=True)
    total_tl: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    lines: Mapped[list] = mapped_column(JSON, default=list)  # [{item, qty, unit, price}]


class StockCount(Base):
    __tablename__ = "stock_counts"
    count_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:10])
    day: Mapped[str] = mapped_column(String, index=True)
    item: Mapped[str] = mapped_column(String)                # hammadde adı veya item_id
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    unit: Mapped[str] = mapped_column(String, default="kg")
    expected_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    counted_by: Mapped[str | None] = mapped_column(String, nullable=True)


MODELS = {"products": Product, "tables": DTable, "staff": Staff, "shifts": Shift,
          "suppliers": Supplier, "invoices": Invoice, "stock": StockCount}


# ------------------------------------------------------------------ şemalar
class Body(BaseModel):
    fields: dict = Field(min_length=1)


def _ensure_tables():
    Base.metadata.create_all(SessionLocal().bind)


# ------------------------------------------------------------------ CRUD
@router.get("/{resource}")
async def list_items(resource: str):
    _ensure_tables()
    m = MODELS.get(resource)
    if not m:
        raise HTTPException(404, f"bilinmeyen kaynak: {resource}")
    s = SessionLocal()
    try:
        rows = s.query(m).all()
        cols = [c.name for c in m.__table__.columns]
        return [{c: _ser(getattr(r, c)) for c in cols} for r in rows]
    finally:
        s.close()


@router.post("/{resource}")
async def create(resource: str, body: Body):
    _ensure_tables()
    m = MODELS.get(resource)
    if not m:
        raise HTTPException(404, f"bilinmeyen kaynak: {resource}")
    s = SessionLocal()
    try:
        obj = m(**{k: v for k, v in body.fields.items()
                   if hasattr(m, k) and v not in (None, "")})
        s.add(obj)
        s.commit()
        s.refresh(obj)
        return {c.name: _ser(getattr(obj, c.name)) for c in m.__table__.columns}
    finally:
        s.close()


@router.put("/{resource}/{item_id}")
async def update(resource: str, item_id: str, body: Body):
    _ensure_tables()
    m = MODELS.get(resource)
    if not m:
        raise HTTPException(404, f"bilinmeyen kaynak: {resource}")
    s = SessionLocal()
    try:
        obj = s.get(m, item_id)
        if not obj:
            raise HTTPException(404, "kayıt yok")
        pk = m.__table__.primary_key.columns[0].name
        for k, v in body.fields.items():
            if hasattr(m, k) and k != pk:
                setattr(obj, k, v)
        s.commit()
        s.refresh(obj)
        return {c.name: _ser(getattr(obj, c.name)) for c in m.__table__.columns}
    finally:
        s.close()


@router.delete("/{resource}/{item_id}")
async def delete(resource: str, item_id: str):
    _ensure_tables()
    m = MODELS.get(resource)
    if not m:
        raise HTTPException(404, f"bilinmeyen kaynak: {resource}")
    s = SessionLocal()
    try:
        obj = s.get(m, item_id)
        if not obj:
            raise HTTPException(404, "kayıt yok")
        s.delete(obj)
        s.commit()
        return {"ok": True}
    finally:
        s.close()


@router.get("/summary/counters")
async def counters():
    _ensure_tables()
    s = SessionLocal()
    try:
        return {
            "products": s.query(Product).count(),
            "tables": s.query(DTable).count(),
            "staff": s.query(Staff).count(),
            "suppliers": s.query(Supplier).count(),
            "invoices_month": s.query(Invoice).filter(
                Invoice.day >= date_t.today().replace(day=1).isoformat()).count(),
        }
    finally:
        s.close()


def _ser(v):
    if isinstance(v, Decimal):
        return str(v)
    return v
