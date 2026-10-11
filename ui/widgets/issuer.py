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


def art_label(issuer: str, label: str = "", px: int = 76):
    """QLabel cuadrado con el icono de plataforma o el monograma (fallback)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from ui.widgets.brands import brand_icon, match_brand
    brand = match_brand(issuer)
    art = QLabel()
    art.setFixedSize(px, px)
    art.setAlignment(Qt.AlignCenter)
    if brand is not None:
        art.setObjectName("tileBrand")
        art.setPixmap(brand_icon(brand).pixmap(int(px * 0.68), int(px * 0.68)))
        art.setToolTip(issuer or label or "")
    else:
        art.setObjectName("tileMono")
        art.setProperty("c", str(color_index(issuer)))
        art.setText(initials(issuer, label))
    return art
