"""Identidad visual por emisor: monograma 2-letras + color determinista.

Decision consciente (AGENTS §20): sin logos de marcas (assets) — offline,
sin dependencias y sin problemas de marcas. Como Google Authenticator:
iniciales + color propio por emisor, legible de un vistazo.
Los 12 colores viven en el QSS (`#tileMono[c="N"]`); aqui solo el indice.
"""
from __future__ import annotations

import hashlib

N_COLORS = 12


def color_index(issuer: str) -> int:
    """Indice 0-11 estable por emisor (sha256, sin `random`)."""
    h = hashlib.sha256((issuer or "?").strip().lower().encode("utf-8")).digest()
    return int.from_bytes(h[:2], "big") % N_COLORS


def initials(issuer: str, label: str = "") -> str:
    base = (issuer or label or "?").strip()
    parts = [p for p in base.replace("@", " ").replace(".", " ").replace("-", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()
