"""TOTP (RFC 6238) con SOLO stdlib: hmac + base64 + struct + time.

Acepta secreto base32 (con/sin relleno, con espacios) o URI
`otpauth://totp/...?secret=...&issuer=...&digits=..&period=..&algorithm=..`.
Soporta SHA-1/256/512, 6-8 digitos, periodo configurable. Nada de red.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
from urllib.parse import parse_qs, urlparse

DEFAULT_DIGITS = 6
DEFAULT_PERIOD = 30
DEFAULT_ALGO = "sha1"
ALLOWED_ALGOS = ("sha1", "sha256", "sha512")
ALLOWED_DIGITS = (6, 7, 8)


def _clean_b32(text: str) -> bytes:
    clean = "".join((text or "").upper().split()).replace("-", "")
    try:
        secret = base64.b32decode(clean + "=" * (-len(clean) % 8))
    except Exception:
        raise ValueError("Secreto TOTP inválido.") from None
    if len(secret) < 10:
        raise ValueError("Secreto TOTP inválido.")
    return secret


def parse_secret(raw: str) -> tuple[bytes, int, int]:
    """Devuelve (secreto, digitos, periodo). Acepta base32 u otpauth://."""
    text = (raw or "").strip()
    digits, period = DEFAULT_DIGITS, DEFAULT_PERIOD
    if text.lower().startswith("otpauth://"):
        try:
            q = parse_qs(urlparse(text).query)
            text = (q.get("secret") or [""])[0]
            digits = int((q.get("digits") or [DEFAULT_DIGITS])[0])
            period = int((q.get("period") or [DEFAULT_PERIOD])[0])
        except Exception:
            raise ValueError("Secreto TOTP inválido.") from None
        if digits not in ALLOWED_DIGITS or period <= 0 or period > 300:
            raise ValueError("Secreto TOTP inválido.")
    secret = _clean_b32(text)
    return secret, digits, period


def _norm_algo(raw: str | None) -> str:
    name = (raw or DEFAULT_ALGO).strip().lower().replace("-", "")
    aliases = {"sha1": "sha1", "sha": "sha1",
               "sha256": "sha256", "sha2": "sha256",
               "sha512": "sha512"}
    algo = aliases.get(name, "")
    if algo not in ALLOWED_ALGOS:
        raise ValueError("Secreto TOTP inválido.")
    return algo


def parse_uri(uri: str) -> dict:
    """Parsea otpauth:// completa. Devuelve dict con issuer/label/secret/digits/period/algo.

    `secret` son los bytes crudos; `secret_b32` es el base32 canonico (sin relleno).
    Los QR futuros se procesan en memoria y se descartan: esta funcion no guarda nada.
    """
    text = (uri or "").strip()
    if not text.lower().startswith("otpauth://"):
        raise ValueError("Secreto TOTP inválido.")
    try:
        parts = urlparse(text)
        if parts.scheme.lower() != "otpauth" or parts.netloc.lower() != "totp":
            raise ValueError("bad")
        q = parse_qs(parts.query)
        secret_raw = (q.get("secret") or [""])[0]
        secret = _clean_b32(secret_raw)
        digits = int((q.get("digits") or [DEFAULT_DIGITS])[0])
        period = int((q.get("period") or [DEFAULT_PERIOD])[0])
        algo = _norm_algo((q.get("algorithm") or [DEFAULT_ALGO])[0])
        issuer_q = ((q.get("issuer") or [""])[0] or "").strip()
        path = parts.path.lstrip("/")
        label = path.strip()
        issuer_p, account = "", label
        if ":" in label:
            issuer_p, account = [s.strip() for s in label.split(":", 1)]
        issuer = issuer_q or issuer_p
    except ValueError:
        raise
    except Exception:
        raise ValueError("Secreto TOTP inválido.") from None
    if digits not in ALLOWED_DIGITS or period <= 0 or period > 300:
        raise ValueError("Secreto TOTP inválido.")
    canon = base64.b32encode(secret).decode("ascii").rstrip("=")
    return {"issuer": issuer[:64], "label": account[:128] or issuer[:128],
            "secret": secret, "secret_b32": canon,
            "digits": digits, "period": period, "algo": algo}


def parse_any(raw: str) -> dict:
    """Acepta secreto suelto o URI completa. Siempre devuelve el dict de parse_uri."""
    text = (raw or "").strip()
    if text.lower().startswith("otpauth://"):
        return parse_uri(text)
    secret = _clean_b32(text)
    canon = base64.b32encode(secret).decode("ascii").rstrip("=")
    return {"issuer": "", "label": "", "secret": secret, "secret_b32": canon,
            "digits": DEFAULT_DIGITS, "period": DEFAULT_PERIOD, "algo": DEFAULT_ALGO}


def format_uri(issuer: str, label: str, secret_b32: str,
               digits: int = DEFAULT_DIGITS, period: int = DEFAULT_PERIOD,
               algo: str = DEFAULT_ALGO) -> str:
    """Reconstruye la URI otpauth:// (para verificar/exportar en memoria)."""
    iss = (issuer or "").strip()
    lab = (label or "").strip() or iss or "Cuenta"
    path = f"{iss}:{lab}" if iss and not lab.startswith(iss) else lab
    alg = _norm_algo(algo)
    return (f"otpauth://totp/{path}?secret={secret_b32}"
            f"&issuer={iss}&digits={int(digits)}&period={int(period)}"
            f"&algorithm={alg.upper()}")


def generate(secret: bytes, at: float | None = None, digits: int = DEFAULT_DIGITS,
             period: int = DEFAULT_PERIOD,
             algo: str = "sha1") -> str:
    """Codigo TOTP (truncamiento dinamico RFC 4226). `at` solo para tests."""
    algo = _norm_algo(algo)
    counter = int((time.time() if at is None else at) // period)
    digest = hmac.new(secret, struct.pack(">Q", counter),
                      getattr(hashlib, algo)).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** digits)).zfill(digits)


def seconds_remaining(at: float | None = None, period: int = DEFAULT_PERIOD) -> int:
    """Segundos hasta el siguiente codigo."""
    now = time.time() if at is None else at
    return int(period - (now % period))
