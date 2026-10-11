"""Iconos SVG de linea inline (monocromos). Cero emojis, cero assets."""
from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap

_STROKE = "#B8A6E0"


def _svg(body: str) -> QIcon:
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
           f'viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" '
           f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
    px = QPixmap()
    px.loadFromData(QByteArray(doc.encode("utf-8")), "SVG")
    return QIcon(px)


def icon(name: str) -> QIcon:
    shapes = {
        "lock": '<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
        "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
        "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
        "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
        "trash": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/>',
        "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
        "up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
        "down": '<path d="M12 5v14M5 12l7 7 7-7"/>',
        "key": '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 5l3 3M14 8l3 3"/>',
        "shield": '<path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z"/>',
    }
    return _svg(shapes.get(name, shapes["shield"]))


def available() -> list[str]:
    return ["lock", "clock", "gear", "plus", "search", "copy",
            "trash", "edit", "up", "down", "key", "shield"]
