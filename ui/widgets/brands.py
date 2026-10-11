"""Iconos de plataforma dibujados a mano (offline, sin assets, sin marcas externas).

Estilo Feather (trazo 1.8, MIT): github/facebook/instagram/linkedin/twitch/telegram(X).
Google G (silueta) y Microsoft (4 cuadros) como formas propias.
TODO lo demas -> monograma (ver issuer.py). Nada de red, nada de fuentes.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap

_STROKE = "#E9E9F2"
_FILL = "#E9E9F2"


def _line(body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
            f'viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


_GITHUB = _line(
    '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61'
    'c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1'
    'S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1'
    'A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7'
    'A3.37 3.37 0 0 0 9 18.13V22"/>')

_FACEBOOK = _line(
    '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>')

_INSTAGRAM = _line(
    '<rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>'
    '<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>'
    '<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>')

_TWITCH = _line(
    '<path d="M21 2H3v16h5v4l4-4h5l4-4V2z"/>'
    '<path d="M11 11V7M16 11V7"/>')

_LINKEDIN = _line(
    '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>'
    '<rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/>')

_TELEGRAM = _line(
    '<line x1="22" y1="2" x2="11" y2="13"/>'
    '<polygon points="22 2 15 22 11 13 2 9 22 2"/>')

_X = _line('<path d="M4 4l16 16M20 4L4 20"/>')

_GOOGLE = (f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
           f'viewBox="0 0 24 24" fill="{_FILL}">'
           '<path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133'
           '-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72'
           's3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307'
           'C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12'
           's5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36'
           '2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"/>'
           '</svg>')

_MICROSOFT = ('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
              'viewBox="0 0 24 24">'
              '<rect x="2.5" y="2.5" width="9.25" height="9.25" fill="#F25022"/>'
              '<rect x="12.25" y="2.5" width="9.25" height="9.25" fill="#7FBA00"/>'
              '<rect x="2.5" y="12.25" width="9.25" height="9.25" fill="#00A4EF"/>'
              '<rect x="12.25" y="12.25" width="9.25" height="9.25" fill="#FFB900"/>'
              '</svg>')

_DOCS = {
    "github": _GITHUB,
    "google": _GOOGLE,
    "microsoft": _MICROSOFT,
    "facebook": _FACEBOOK,
    "instagram": _INSTAGRAM,
    "x": _X,
    "twitch": _TWITCH,
    "linkedin": _LINKEDIN,
    "telegram": _TELEGRAM,
}

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "github": ("github",),
    "google": ("google", "gmail", "youtube", "gsuite", "workspace"),
    "microsoft": ("microsoft", "outlook", "hotmail", "live.com", "office", "xbox",
                  "onedrive", "teams", "azure"),
    "facebook": ("facebook", "meta"),
    "instagram": ("instagram",),
    "x": ("twitter",),
    "twitch": ("twitch",),
    "linkedin": ("linkedin",),
    "telegram": ("telegram",),
}


def match_brand(issuer: str) -> str | None:
    """Nombre del icono para un emisor, o None (monograma)."""
    text = (issuer or "").strip().lower()
    if not text:
        return None
    if text == "x":
        return "x"
    for name, keys in _KEYWORDS.items():
        if any(k in text for k in keys):
            return name
    return None


def brand_icon(name: str) -> QIcon:
    px = QPixmap()
    px.loadFromData(QByteArray(_DOCS[name].encode("utf-8")), "SVG")
    return QIcon(px)


def brand_names() -> list[str]:
    return sorted(_DOCS)
