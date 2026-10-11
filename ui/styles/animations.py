"""Animaciones sutiles 150-300ms. Respetan reduced-motion en caliente."""
from __future__ import annotations

import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

_reduced = os.environ.get("REDUCED_MOTION") == "1"


def set_reduced(value: bool) -> None:
    global _reduced
    _reduced = bool(value)


def enabled() -> bool:
    return not _reduced


def _alive(w: QWidget) -> bool:
    """False si el objeto C++ ya fue borrado (evita crash libshiboken).

    Las listas (cuentas) borran filas y los QTimer.singleShot de `stagger`
    pueden dispararse despues: sin este guard, RuntimeError y traceback.
    """
    try:
        w.objectName()
        return True
    except RuntimeError:
        return False


def _cleanup(w: QWidget):
    try:
        w.setGraphicsEffect(None)
    except (RuntimeError, Exception):
        pass


def _fade(w: QWidget, ms: int, easing=None) -> None:
    if not enabled() or not _alive(w):
        return
    try:
        if w.graphicsEffect() is not None:
            return
    except RuntimeError:
        return
    try:
        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        a = QPropertyAnimation(eff, b"opacity", w)
        a.setDuration(ms)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        if easing is not None:
            a.setEasingCurve(easing)
        a.finished.connect(lambda: _cleanup(w))
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    except RuntimeError:
        pass


def fade_in(w: QWidget, ms: int = 180) -> None:
    _fade(w, ms)


def rise_in(w: QWidget, ms: int = 220) -> None:
    """Entrada: fade + curva suave. No-op si hay efecto activo o murió."""
    _fade(w, ms, QEasingCurve.OutCubic)


def stagger(widgets: list[QWidget], base_ms: int = 200) -> None:
    """Solo entre HERMANOS (nunca padre+hijos): retrasa rise_in de cada uno."""
    if not enabled():
        return
    from PySide6.QtCore import QTimer
    for i, w in enumerate(widgets):
        QTimer.singleShot(i * 40, lambda w=w: rise_in(w, base_ms) if _alive(w) else None)


def shake(w: QWidget) -> None:
    if not enabled() or not _alive(w):
        return
    try:
        a = QPropertyAnimation(w, b"pos", w)
        a.setDuration(220)
        p = w.pos()
        x0, y0 = p.x(), p.y()
        cls = p.__class__
        a.setKeyValueAt(0.0, p)
        a.setKeyValueAt(0.25, cls(x0 + 7, y0))
        a.setKeyValueAt(0.5, cls(x0 - 5, y0))
        a.setKeyValueAt(0.75, cls(x0 + 3, y0))
        a.setKeyValueAt(1.0, p)
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    except RuntimeError:
        pass


def press_scale(w: QWidget) -> None:
    if not enabled() or not _alive(w):
        return
    try:
        if w.graphicsEffect() is not None:
            return
    except RuntimeError:
        return
    try:
        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        a = QPropertyAnimation(eff, b"opacity", w)
        a.setDuration(150)
        a.setStartValue(0.55)
        a.setEndValue(1.0)
        a.finished.connect(lambda: _cleanup(w))
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    except RuntimeError:
        pass
