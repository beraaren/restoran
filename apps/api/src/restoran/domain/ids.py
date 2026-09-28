"""UUIDv7 üretici — Python 3.12'de uuid.uuid7 yok, elle kurulur (RFC 9562).

Düzen: 48-bit ms timestamp | 4-bit versiyon (0b0111) | 12-bit rand_a |
2-bit varyant (0b10) | 62-bit rand_b. Zaman sıralı olduğu için PK index'leri
lokal kalır.
"""
from __future__ import annotations

import os
import time
from uuid import UUID


def uuid7() -> UUID:
    ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")  # 80 rastgele bit
    rand_a = (rand >> 62) & 0xFFF
    rand_b = rand & ((1 << 62) - 1)
    value = (ms << 80) | (0b0111 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return UUID(int=value)
