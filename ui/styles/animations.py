"""Animaciones sutiles 150-300ms. Respetan reduced-motion en caliente."""
from __future__ import annotations

import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

_reduced = os.environ.get("REDUCED_MOTION") == "1"


def set_reduced(value: bool) -> None:
    global _reduced
    _reduced = bool(value)


def enabled() -> bool:
    return not _reduced


def _cleanup(w: QWidget):
    try:
        w.setGraphicsEffect(None)
    except Exception:
        pass


def fade_in(w: QWidget, ms: int = 180) -> None:
    if not enabled() or w.graphicsEffect() is not None:
        return
    eff = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(eff)
    a = QPropertyAnimation(eff, b"opacity", w)
    a.setDuration(ms)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.finished.connect(lambda: _cleanup(w))
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def rise_in(w: QWidget, ms: int = 220) -> None:
    """Entrada: fade + subida leve. No-op si ya hay efecto activo."""
    if not enabled() or w.graphicsEffect() is not None:
        return
    eff = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(eff)
    a = QPropertyAnimation(eff, b"opacity", w)
    a.setDuration(ms)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.setEasingCurve(QEasingCurve.OutCubic)
    a.finished.connect(lambda: _cleanup(w))
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def stagger(widgets: list[QWidget], base_ms: int = 200) -> None:
    """Solo entre HERMANOS (nunca padre+hijos): retrasa rise_in de cada uno."""
    if not enabled():
        return
    from PySide6.QtCore import QTimer
    for i, w in enumerate(widgets):
        QTimer.singleShot(i * 40, lambda w=w: rise_in(w, base_ms))


def shake(w: QWidget) -> None:
    if not enabled():
        return
    from PySide6.QtCore import QPropertyAnimation
    a = QPropertyAnimation(w, b"pos", w)
    a.setDuration(220)
    p = w.pos()
    a.setKeyValueAt(0.0, p)
    a.setKeyValueAt(0.25, p + Qt.QPoint(7, 0) if hasattr(Qt, "QPoint") else p)
    a.finished.connect(lambda: None)
    try:
        x0 = p.x()
        a.setKeyValueAt(0.25, p.__class__(x0 + 7, p.y()))
        a.setKeyValueAt(0.5, p.__class__(x0 - 5, p.y()))
        a.setKeyValueAt(0.75, p.__class__(x0 + 3, p.y()))
        a.setKeyValueAt(1.0, p)
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    except Exception:
        pass


def press_scale(w: QWidget) -> None:
    if not enabled() or w.graphicsEffect() is not None:
        return
    eff = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(eff)
    a = QPropertyAnimation(eff, b"opacity", w)
    a.setDuration(150)
    a.setStartValue(0.55)
    a.setEndValue(1.0)
    a.finished.connect(lambda: _cleanup(w))
    a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
