"""Toasts bottom: slide-in + auto-dismiss 3s."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget


def show_toast(parent: QWidget, text: str, ms: int = 3000) -> None:
    tip = QLabel(text, parent)
    tip.setObjectName("toast")
    tip.setWindowFlags(Qt.SubWindow)
    tip.adjustSize()
    try:
        x = parent.width() - tip.width() - 16
        y = parent.height() - tip.height() - 16
        tip.move(max(0, x), max(0, y))
    except Exception:
        pass
    tip.show()
    tip.raise_()
    try:
        a = QPropertyAnimation(tip, b"pos", tip)
        a.setDuration(180)
        end = tip.pos()
        a.setStartValue(QPoint(end.x(), end.y() + 18))
        a.setEndValue(end)
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    except Exception:
        pass
    QTimer.singleShot(ms, tip.deleteLater)
