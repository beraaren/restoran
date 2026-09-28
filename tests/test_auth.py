"""Faz 0 auth akışı testleri — gerçek Postgres + seed'li demo verisi.

Login/PIN, JWT claims, require(perm) zinciri ve yönetim endpoint'leri.
"""
from __future__ import annotations

PATRON = {"venue_slug": "taksim", "employee_id_or_card": "CARD-001", "pin": "1111"}
GARSON = {"venue_slug": "taksim", "employee_id_or_card": "CARD-003", "pin": "3333"}


def login(client, body):
    r = client.post("/auth/login/pin", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_pin_doğru(client):
    data = login(client, PATRON)
    emp = data["employee"]
    assert emp["role"] == "Patron"
    assert emp["full_name"] == "Ayşe Patron"
    assert "admin.users" in emp["permissions"]
    assert data["token_type"] == "bearer" and data["access_token"]


def test_login_yanlış_pin_401(client):
    body = dict(PATRON, pin="9999")
    assert client.post("/auth/login/pin", json=body).status_code == 401


def test_login_bilinmeyen_calisan_401(client):
    body = dict(PATRON, employee_id_or_card="CARD-YOK")
    assert client.post("/auth/login/pin", json=body).status_code == 401


def test_login_bilinmeyen_venue_401(client):
    body = dict(PATRON, venue_slug="ankara")
    assert client.post("/auth/login/pin", json=body).status_code == 401


def test_login_employee_id_ile_de_girilir(client):
    data = login(client, PATRON)
    emp_id = data["employee"]["employee_id"]
    body = {"venue_slug": "demo",  # tenant slug'ı da venue çözüyor
            "employee_id_or_card": emp_id, "pin": "1111"}
    login(client, body)  # 200 beklenir, assert login içinde


def test_me_claims_döner(client):
    token = login(client, GARSON)["access_token"]
    r = client.get("/auth/me", headers=auth(token))
    assert r.status_code == 200
    claims = r.json()
    assert claims["role"] == "Garson"
    assert claims["perms"] == ["ticket.create", "payment.take"]
    assert claims["sub"] and claims["venue_id"]
    assert claims["terminal_id"] is None


def test_token_yoksa_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/admin/identity/employees").status_code == 401


def test_bozuk_token_401(client):
    r = client.get("/auth/me", headers=auth("sahte.token.deger"))
    assert r.status_code == 401


def test_garson_admin_endpoint_403(client):
    token = login(client, GARSON)["access_token"]
    r = client.get("/admin/identity/employees", headers=auth(token))
    assert r.status_code == 403
    assert "admin.users" in r.json()["detail"]


def test_patron_admin_endpoint_200(client):
    token = login(client, PATRON)["access_token"]
    r = client.get("/admin/identity/employees", headers=auth(token))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 5
    assert all("pin_hash" not in row for row in rows)


def test_terminal_create_require_zinciri(client):
    import uuid

    patron = login(client, PATRON)["access_token"]
    garson = login(client, GARSON)["access_token"]
    venues = client.get("/admin/identity/venues", headers=auth(patron)).json()
    venue_id = next(v["id"] for v in venues if v["slug"] == "taksim")
    code = f"TEST-KIOSK-{uuid.uuid4().hex[:6]}"  # her koşuda benzersiz: test idempotent kalır
    body = {"venue_id": venue_id, "code": code, "kind": "kiosk",
            "name": "test terminal"}
    # garson: 403 (require zinciri)
    assert client.post("/admin/identity/terminals", json=body,
                       headers=auth(garson)).status_code == 403
    # patron: 201
    r = client.post("/admin/identity/terminals", json=body, headers=auth(patron))
    assert r.status_code == 201, r.text
    # aynı kod tekrar: 409
    assert client.post("/admin/identity/terminals", json=body,
                       headers=auth(patron)).status_code == 409


def test_employee_crud_pin_rotate(client):
    patron = login(client, PATRON)["access_token"]
    venues = client.get("/admin/identity/venues", headers=auth(patron)).json()
    venue_id = next(v["id"] for v in venues if v["slug"] == "taksim")
    roles = client.get("/admin/identity/roles", headers=auth(patron),
                       params={"venue_id": venue_id}).json()
    garson_role = next(x["id"] for x in roles if x["name"] == "Garson")

    created = client.post("/admin/identity/employees", headers=auth(patron), json={
        "venue_id": venue_id, "full_name": "Test Garson", "pin": "4321",
        "card_code": "CARD-TEST", "role_id": garson_role})
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]

    # yeni PIN ile giriş
    body = {"venue_slug": "taksim", "employee_id_or_card": "CARD-TEST", "pin": "4321"}
    assert login(client, body)["employee"]["full_name"] == "Test Garson"

    # PIN rotate et -> eskisi geçmez, yenisi geçer
    r = client.put(f"/admin/identity/employees/{emp_id}", headers=auth(patron),
                   json={"pin": "8765"})
    assert r.status_code == 200
    stale = {"venue_slug": "taksim", "employee_id_or_card": "CARD-TEST", "pin": "4321"}
    assert client.post("/auth/login/pin", json=stale).status_code == 401

    # pasife al -> 403
    client.put(f"/admin/identity/employees/{emp_id}", headers=auth(patron),
               json={"active": False})
    inactive = {"venue_slug": "taksim", "employee_id_or_card": "CARD-TEST", "pin": "8765"}
    assert client.post("/auth/login/pin", json=inactive).status_code == 403

    # temizle
    assert client.delete(f"/admin/identity/employees/{emp_id}",
                         headers=auth(patron)).status_code == 200


def test_rol_yetkisi_guncelinde_jwt_yeni_perms_taşır(client):
    patron = login(client, PATRON)["access_token"]
    roles = client.get("/admin/identity/roles", headers=auth(patron)).json()
    askci = next(x for x in roles if x["name"] == "Aşçı")
    body = {"venue_slug": "taksim", "employee_id_or_card": "CARD-004", "pin": "4444"}
    before = login(client, body)
    assert "audit.view" not in before["employee"]["permissions"]
    # aşçıya audit.view ekle, token'ı yeniden al, kontrol et, geri al
    r = client.put(f"/admin/identity/roles/{askci['id']}", headers=auth(patron),
                   json={"permissions": askci["permissions"] + ["audit.view"]})
    assert r.status_code == 200
    after = login(client, body)
    assert "audit.view" in after["employee"]["permissions"]
    me = client.get("/auth/me", headers=auth(after["access_token"])).json()
    assert "audit.view" in me["perms"]
    client.put(f"/admin/identity/roles/{askci['id']}", headers=auth(patron),
               json={"permissions": askci["permissions"]})
