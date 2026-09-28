"""Pytest ortak ayarları — Faz 0 auth testleri gerçek Postgres'e koşar.

settings.DATABASE_URL defaultu (localhost:5433) kullanılır; seed session
boyunca bir kez idempotent çalışır.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def seeded():
    from restoran.domain.seed import run
    return run()


@pytest.fixture(scope="session")
def client():
    from restoran.api.main import app
    from starlette.testclient import TestClient
    # lifespan başlatılmıyor: bootstrap sqlite/evaluator döngüsü auth testleri
    # için gerekmiyor, token harcamıyor
    return TestClient(app)
