"""Domain DB katmanı — legacy `restoran.store.db`'den BAĞIMSIZ ikinci Base.

Faz 0'da sadece kimlik tabloları burada; Postgres (settings.DATABASE_URL).
Legacy event store SQLite defaultuyla yaşar, Faz 4'te birleşir.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..api.settings import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False,
                            class_=Session)
