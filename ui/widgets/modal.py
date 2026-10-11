"""ModalHost compacto: dim pintado a mano + fade/slide + bloqueo total."""
from __future__ import annotations

from PySide6.QtCore import Property, QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget


class ModalHost(QDialog):
    """Dialog translucido que oscurece a mano (~53%) y centra una tarjeta."""

    def __init__(self, parent: QWidget | None = None, dim: str = "#000000"):
        super().__init__(parent)
        self._dimColor = dim
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setContentsMargins(24, 24, 24, 24)
        self.card = QWidget(self)
        self.card.setObjectName("card")
        self.card.setMinimumWidth(300)
        self.card.setMaximumWidth(360)
        lay.addWidget(self.card)

    def getDimColor(self) -> str:
        return self._dimColor

    def setDimColor(self, value: str) -> None:
        self._dimColor = value
        self.update()

    dimColor = Property(str, getDimColor, setDimColor)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        try:
            c = QColor(self._dimColor)
            c.setAlphaF(0.53)
            p.fillRect(self.rect(), c)
        finally:
            p.end()

    def open_animated(self) -> None:
        from ui.styles import animations as anim
        parent = self.parentWidget()
        if parent is not None:
            try:
                top = parent.mapToGlobal(parent.rect().topLeft())
                self.setGeometry(QRect(top, parent.size()))
            except Exception:
                pass
        self.show()
        anim.fade_in(self.card, 200)

    @staticmethod
    def wrap(parent: QWidget, inner: QWidget, title: str = "") -> "ModalHost":
        host = ModalHost(parent)
        lay = QVBoxLayout(host.card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        lay.addWidget(inner)
        if title:
            host.setWindowTitle(title)
        return host
