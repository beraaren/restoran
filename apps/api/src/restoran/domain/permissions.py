"""Yetki sabitleri — JWT claims ve Role.permissions burada tanımlı listeyle konuşur."""
from __future__ import annotations

TICKET_CREATE = "ticket.create"
TICKET_VOID = "ticket.void"
PAYMENT_TAKE = "payment.take"
DRAWER_OPEN = "drawer.open"
DAY_CLOSE = "day.close"
KDS_VIEW = "kds.view"
KDS_DONE = "kds.done"
STOCK_COUNT = "stock.count"
MENU_EDIT = "menu.edit"
AUDIT_VIEW = "audit.view"
ADMIN_USERS = "admin.users"
ADMIN_BILLING = "admin.billing"

PERMISSIONS: list[str] = [
    TICKET_CREATE, TICKET_VOID, PAYMENT_TAKE, DRAWER_OPEN, DAY_CLOSE,
    KDS_VIEW, KDS_DONE, STOCK_COUNT, MENU_EDIT, AUDIT_VIEW,
    ADMIN_USERS, ADMIN_BILLING,
]
