"""Aktör durum makineleri — onaylanan planın 1. bölümünün kod karşılığı.

Durum adları planla birebir aynı; geçişler normalize sinyal adlarıyla tetiklenir.
Sinyaller router (signals.py) tarafından PosEvent/VisionEvent'ten üretilir.
"""
from __future__ import annotations

from .machine import StateMachine

# ---------------------------------------------------------------- Plate/Ürün
PLATE_TRANSITIONS = {
    # (mevcut durum, sinyal): hedef
    ("SIPARIS_EDILDI", "prep_detected"):        {"to": "HAZIRLANIYOR"},
    ("HAZIRLANIYOR", "left_kitchen"):           {"to": "HAZIRLANDI"},
    ("SIPARIS_EDILDI", "left_kitchen"):         {"to": "HAZIRLANDI"},  # prep görünmediyse atlama
    ("HAZIRLANDI", "in_transit"):               {"to": "TESLIM_EDILIYOR"},
    ("TESLIM_EDILIYOR", "served"):              {"to": "YENIYOR"},
    ("HAZIRLANDI", "served"):                   {"to": "YENIYOR"},     # taşıma kamerasız atlanabilir
    ("YENIYOR", "cleared"):                     {"to": "BITTI"},
    ("BITTI", "paid"):                          {"to": "ODEMESI_ALINDI"},
    ("YENIYOR", "paid"):                        {"to": "ODEMESI_ALINDI"},
}

Plate = StateMachine("plate", "SIPARIS_EDILDI", PLATE_TRANSITIONS)

# ---------------------------------------------------------------- Masa
TABLE_TRANSITIONS = {
    ("BOS", "customer_seated"):      {"to": "DOLU"},
    ("DOLU", "ticket_fired"):        {"to": "SIPARIS_VAR"},
    ("DOLU", "served"):              {"to": "SERVIS_EDILDI"},  # ticketsiz servis de izlenir
    ("SIPARIS_VAR", "served"):       {"to": "SERVIS_EDILDI"},
    ("SERVIS_EDILDI", "customer_left"): {"to": "TEMIZLIK_BEKLIYOR"},
    ("TEMIZLIK_BEKLIYOR", "table_clean"): {"to": "BOS"},
    ("DOLU", "customer_left"):       {"to": "TEMIZLIK_BEKLIYOR"},
    ("SIPARIS_VAR", "customer_left"): {"to": "TEMIZLIK_BEKLIYOR"},
}

Table = StateMachine("table", "BOS", TABLE_TRANSITIONS)

# ---------------------------------------------------------------- Müşteri
CUSTOMER_TRANSITIONS = {
    ("GIRDI", "waiting_table"):      {"to": "MASA_BEKLIYOR"},
    ("GIRDI", "seated"):             {"to": "OTURDU"},
    ("MASA_BEKLIYOR", "seated"):     {"to": "OTURDU"},
    ("OTURDU", "ticket_fired"):      {"to": "YEMEK_BEKLIYOR"},  # sipariş aşaması POS'ta görünür
    ("OTURDU", "served"):            {"to": "YIYOR"},
    ("YEMEK_BEKLIYOR", "served"):    {"to": "YIYOR"},
    ("YIYOR", "cleared"):            {"to": "BITTI"},
    ("BITTI", "paid"):               {"to": "ODEDI"},
    ("YIYOR", "left"):               {"to": "BITTI"},
}

Customer = StateMachine("customer", "GIRDI", CUSTOMER_TRANSITIONS)

# ---------------------------------------------------------------- Aşçı
CHEF_TRANSITIONS = {
    ("BOSTA", "prep_started"):   {"to": "SIPARIS_UZERINDE"},
    ("SIPARIS_UZERINDE", "prep_paused"): {"to": "BEKLEMEDE"},
    ("BEKLEMEDE", "prep_started"): {"to": "SIPARIS_UZERINDE"},
    ("SIPARIS_UZERINDE", "dish_ready"): {"to": "HAZIR_TESLIM"},
    ("HAZIR_TESLIM", "prep_started"): {"to": "SIPARIS_UZERINDE"},
    ("HAZIR_TESLIM", "idle_timeout"): {"to": "BOSTA"},
}

Chef = StateMachine("chef", "BOSTA", CHEF_TRANSITIONS)

# ---------------------------------------------------------------- Garson
WAITER_TRANSITIONS = {
    ("BEKLEMEDE", "order_taking"):   {"to": "SIPARIS_ALIYOR"},
    ("BEKLEMEDE", "pos_interaction"): {"to": "EKRANA_GIRIYOR"},
    ("BEKLEMEDE", "carrying"):       {"to": "TASIYOR"},
    ("SIPARIS_ALIYOR", "pos_interaction"): {"to": "EKRANA_GIRIYOR"},
    ("SIPARIS_ALIYOR", "carrying"):  {"to": "TASIYOR"},
    ("EKRANA_GIRIYOR", "carrying"):  {"to": "TASIYOR"},
    ("TASIYOR", "serving"):          {"to": "SERVIS_YAPIYOR"},
    ("SERVIS_YAPIYOR", "idle_timeout"): {"to": "BEKLEMEDE"},
    ("SIPARIS_ALIYOR", "idle_timeout"): {"to": "BEKLEMEDE"},
    ("EKRANA_GIRIYOR", "idle_timeout"): {"to": "BEKLEMEDE"},
    ("TASIYOR", "idle_timeout"):     {"to": "BEKLEMEDE"},
}

Waiter = StateMachine("waiter", "BEKLEMEDE", WAITER_TRANSITIONS)

ACTORS = {m.name: m for m in (Plate, Table, Customer, Chef, Waiter)}
