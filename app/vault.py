"""Vault: UNICO lugar con criptografia. Argon2id + AES-256-GCM.

Copia autocontenida del patron del gestor. NADA compartido entre repos:
este modulo no importa nada del Password Manager.
"""
from __future__ import annotations

import base64
import ctypes
import secrets

from argon2 import PasswordHasher
from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Parametros NO negociables (ver AGENTS.md)
TIME_COST = 3
MEMORY_COST = 65536  # 64 MiB
PARALLELISM = 4
HASH_LEN = 32
SALT_LEN = 16
NONCE_LEN = 12
PREFIX = "v1."

_ph = PasswordHasher(time_cost=TIME_COST, memory_cost=MEMORY_COST,
                     parallelism=PARALLELISM, hash_len=HASH_LEN, salt_len=SALT_LEN)


def generate_salt(n: int = SALT_LEN) -> bytes:
    return secrets.token_bytes(n)


def derive_key(master: str, salt: bytes) -> bytearray:
    """Deriva la KEK de 32 bytes con Argon2id (mutable para poder borrarla)."""
    raw = hash_secret_raw(master.encode("utf-8"), salt,
                          time_cost=TIME_COST, memory_cost=MEMORY_COST,
                          parallelism=PARALLELISM, hash_len=HASH_LEN,
                          type=Type.ID)
    return bytearray(raw)


def hash_master(master: str) -> str:
    return _ph.hash(master)


def verify_master(stored_hash: str, master: str) -> bool:
    try:
        return _ph.verify(stored_hash, master)
    except Exception:
        return False


def encrypt(key: bytes | bytearray, plaintext: bytes) -> str:
    nonce = secrets.token_bytes(NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return PREFIX + base64.b64encode(nonce + ct).decode("ascii")


def decrypt(key: bytes | bytearray, blob: str) -> bytes:
    if not blob.startswith(PREFIX):
        raise ValueError("datos corruptos o clave incorrecta")
    try:
        raw = base64.b64decode(blob[len(PREFIX):])
        nonce, ct = raw[:NONCE_LEN], raw[NONCE_LEN:]
        return AESGCM(key).decrypt(nonce, ct, None)
    except (InvalidTag, Exception):
        raise ValueError("datos corruptos o clave incorrecta")


def wipe(data: bytearray | bytes | None) -> bool:
    """Sobreescribe la clave en memoria. Solo funciona con bytearray mutable."""
    if not isinstance(data, bytearray):
        return False
    try:
        ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(data)), 0, len(data))
        for i in range(len(data)):
            data[i] = 0
        return True
    except Exception:
        return False
