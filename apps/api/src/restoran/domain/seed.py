"""Faz 0 seed — demo tenant + Taksim venue + 4 terminal + 5 rol + 5 çalışan.

İdempotent: slug/name ile varlık kontrolü yapılır, varsa atlanır.
Çalıştırma: .venv/bin/python -m restoran.domain.seed  (Postgres gerekiyor)
"""
from __future__ import annotations

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .identity import Employee, Role, Tenant, Terminal, Venue
from .permissions import (
    ADMIN_BILLING,
    DRAWER_OPEN,
    KDS_DONE,
    KDS_VIEW,
    PAYMENT_TAKE,
    PERMISSIONS,
    TICKET_CREATE,
)

# ------------------------------------------------------------------ roller
SEED_ROLES: dict[str, list[str]] = {
    "Patron": list(PERMISSIONS),
    "Müdür": [p for p in PERMISSIONS if p != ADMIN_BILLING],
    "Garson": [TICKET_CREATE, PAYMENT_TAKE],
    "Aşçı": [KDS_VIEW, KDS_DONE],
    "Kasiyer": [TICKET_CREATE, PAYMENT_TAKE, DRAWER_OPEN],
}

# --------------------------------------------------------------- çalışanlar
# (full_name, rol, pin, card_code)
SEED_EMPLOYEES = [
    ("Ayşe Patron", "Patron", "1111", "CARD-001"),
    ("Mehmet Müdür", "Müdür", "2222", "CARD-002"),
    ("Gül Garson", "Garson", "3333", "CARD-003"),
    ("Ali Aşçı", "Aşçı", "4444", "CARD-004"),
    ("Zeynep Kasiyer", "Kasiyer", "5555", "CARD-005"),
]

SEED_TERMINALS = [
    ("KASA-1", "pos", "Kasa 1"),
    ("SALON-1", "floor", "Salon servis"),
    ("MUTFAK-1", "kds", "Mutfak ekranı"),
    ("KIOSK-1", "kiosk", "Self servis"),
]


def run() -> dict:
    """Tohumları eker; {'created': [...], 'skipped': [...]} döner."""
    from ..auth.security import hash_pin as _hash  # döngüsel import'tan kaçın
    created: list[str] = []
    skipped: list[str] = []
    Base.metadata.create_all(engine)  # migration'dan bağımsız güvenlik ağı
    s = SessionLocal()
    try:
        tenant = s.scalar(select(Tenant).where(Tenant.slug == "demo"))
        if not tenant:
            tenant = Tenant(name="Demo Restoran A.Ş.", slug="demo")
            s.add(tenant)
            s.flush()
            created.append("tenant:demo")
        else:
            skipped.append("tenant:demo")

        venue = s.scalar(select(Venue).where(Venue.tenant_id == tenant.id,
                                             Venue.slug == "taksim"))
        if not venue:
            venue = Venue(tenant_id=tenant.id, name="Taksim", slug="taksim",
                          address="İstiklal Cad. No:1", timezone="Europe/Istanbul")
            s.add(venue)
            s.flush()
            created.append("venue:taksim")
        else:
            skipped.append("venue:taksim")

        for code, kind, name in SEED_TERMINALS:
            if s.scalar(select(Terminal).where(Terminal.venue_id == venue.id,
                                               Terminal.code == code)):
                skipped.append(f"terminal:{code}")
                continue
            s.add(Terminal(venue_id=venue.id, code=code, kind=kind, name=name))
            created.append(f"terminal:{code}")

        roles: dict[str, Role] = {}
        for rname, perms in SEED_ROLES.items():
            r = s.scalar(select(Role).where(Role.venue_id == venue.id,
                                            Role.name == rname))
            if not r:
                r = Role(venue_id=venue.id, name=rname, permissions=perms)
                s.add(r)
                s.flush()
                created.append(f"role:{rname}")
            else:
                skipped.append(f"role:{rname}")
            roles[rname] = r

        for full_name, rname, pin, card in SEED_EMPLOYEES:
            if s.scalar(select(Employee).where(Employee.venue_id == venue.id,
                                               Employee.full_name == full_name)):
                skipped.append(f"employee:{full_name}")
                continue
            s.add(Employee(venue_id=venue.id, full_name=full_name,
                           pin_hash=_hash(pin), card_code=card,
                           role_id=roles[rname].id))
            created.append(f"employee:{full_name}")

        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
    return {"created": created, "skipped": skipped}


if __name__ == "__main__":
    result = run()
    print("seed ok")
    for line in result["created"]:
        print("  +", line)
    for line in result["skipped"]:
        print("  =", line)
