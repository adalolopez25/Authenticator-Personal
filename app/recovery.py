"""Kit de recuperacion offline: la unica salida si se olvida la master.

Mismo diseno que el gestor, copiado (cero red, cero backend):
R aleatoria de 256 bits, nunca en claro. En `meta` solo dos blobs
AES-256-GCM. El CODIGO se muestra UNA vez.
Este modulo NO importa `cryptography`/`argon2`: todo pasa por vault.
"""
from __future__ import annotations

import base64
import hashlib
import secrets

from app import vault

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_GROUP = 5
_KEY_LEN = 32
_CHECK_LEN = 2
RECOVERY_PLAINTEXT = b"VAULT-OK"


def encode(raw: bytes) -> str:
    text = base64.b32encode(bytes(raw)).decode("ascii")
    text = text.rstrip("=").translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", _ALPHABET))
    return "-".join(text[i:i + _GROUP] for i in range(0, len(text), _GROUP))


def decode(code: str) -> bytes:
    clean = "".join(code.upper().split()).replace("-", "")
    try:
        std = clean.translate(str.maketrans(_ALPHABET,
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"))
        pad = "=" * (-len(std) % 8)
        raw = base64.b32decode(std + pad)
    except Exception:
        raise ValueError("Código de recuperación inválido.") from None
    if len(raw) != _KEY_LEN + _CHECK_LEN:
        raise ValueError("Código de recuperación inválido.")
    data, check = raw[:_KEY_LEN], raw[_KEY_LEN:]
    if hashlib.sha256(data).digest()[:_CHECK_LEN] != check:
        raise ValueError("Código de recuperación inválido.")
    return data


def generate() -> tuple[bytes, str]:
    raw = secrets.token_bytes(_KEY_LEN)
    code = encode(raw + hashlib.sha256(raw).digest()[:_CHECK_LEN])
    return raw, code


def make_wraps(kek: bytes | bytearray) -> tuple[str, str, str]:
    raw, code = generate()
    check = vault.encrypt(raw, RECOVERY_PLAINTEXT)
    wrap = vault.encrypt(raw, bytes(kek))
    return check, wrap, code


def recover_kek(code: str, check_blob: str, wrap_blob: str) -> bytearray:
    try:
        raw = decode(code)
    except ValueError:
        raise ValueError("Código de recuperación inválido.") from None
    try:
        if vault.decrypt(raw, check_blob) != RECOVERY_PLAINTEXT:
            raise ValueError("Código de recuperación inválido.")
        return bytearray(vault.decrypt(raw, wrap_blob))
    except ValueError:
        raise ValueError("Código de recuperación inválido.") from None
