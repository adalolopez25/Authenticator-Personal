"""InfoBox: aviso estilizado con icono + tono (info/warn/danger/ok).

REGLA DE MICROCOPY (AGENTS §19): en la UI solo vive texto de ACCION
(que hacer / que pasa si). Cero documentacion de procesos internos
(KDF, backoff, MVP, NTP...): eso va a tooltips, README o AGENTS.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui.widgets.icons import icon

_TONE_ICON = {"info": "info", "warn": "alert", "danger": "alert", "ok": "check"}


class InfoBox(QWidget):
    def __init__(self, text: str, tone: str = "info", parent=None):
        super().__init__(parent)
        if tone not in ("info", "warn", "danger", "ok"):
            tone = "info"
        self.setObjectName("infoBox")
        self.setProperty("tone", tone)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)
        art = QLabel()
        art.setPixmap(icon(_TONE_ICON[tone]).pixmap(20, 20))
        art.setFixedSize(22, 22)
        lay.addWidget(art)
        msg = QLabel(text)
        msg.setWordWrap(True)
        lay.addWidget(msg, 1)
