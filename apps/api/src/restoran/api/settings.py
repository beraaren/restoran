"""Faz 0 ayarları — domain engine ve auth burada yaşar.

Not: legacy `restoran.store.db` kendi DATABASE_URL env okumaya devam eder
(SQLite default); bu Settings YENİ domain/Alembic tarafı için geçerlidir.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://restoran:restoran@localhost:5433/restoran"
    JWT_SECRET: str = "dev-degiştir-bunu"
    JWT_TTL_S: int = 43200  # 12 saat — vardiya süresi
    ENV: str = "dev"


settings = Settings()
