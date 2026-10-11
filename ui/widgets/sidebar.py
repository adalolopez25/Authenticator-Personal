"""Sidebar de navegacion (solo modo escritorio/app). Colapsable con animacion.

Header con marca + boton chevron para ocultar/mostrar (como la otra app).
Abajo: bloquear + version.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from ui.styles import animations as anim
from ui.widgets.icons import icon

EXPANDED = 252
COLLAPSED = 72


class Sidebar(QWidget):
    navigated = Signal(str)  # accounts | add | trash | prefs

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(EXPANDED)
        self._collapsed = False
        self._trash_n = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(6)
        # Header: marca + ocultar
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        self.brand_icon = QLabel()
        self.brand_icon.setPixmap(icon("lock").pixmap(22, 22))
        self.brand_icon.setFixedSize(26, 26)
        head.addWidget(self.brand_icon)
        self.brand = QLabel("Authenticator")
        self.brand.setObjectName("brand")
        head.addWidget(self.brand, 1)
        self.b_fold = QPushButton()
        self.b_fold.setObjectName("toolBtn")
        self.b_fold.setIcon(icon("chev_l"))
        self.b_fold.setToolTip("Ocultar barra lateral")
        self.b_fold.setFixedSize(32, 32)
        self.b_fold.clicked.connect(self.toggle)
        head.addWidget(self.b_fold)
        lay.addLayout(head)
        lay.addSpacing(10)
        cap = QLabel("PRINCIPAL")
        cap.setObjectName("navCap")
        lay.addWidget(cap)
        self._cap = cap
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        self.badges: dict[str, QLabel] = {}
        for key, label, ic in (("accounts", "Cuentas", "grid"),
                               ("add", "Añadir cuenta", "plus"),
                               ("trash", "Papelera", "trash"),
                               ("prefs", "Preferencias", "sliders")):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            b = QPushButton(label)
            b.setObjectName("sideBtn")
            b.setIcon(icon(ic))
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self._go(k))
            self.group.addButton(b)
            self.buttons[key] = b
            row.addWidget(b, 1)
            badge = QLabel("")
            badge.setObjectName("badge")
            badge.setVisible(False)
            self.badges[key] = badge
            row.addWidget(badge)
            lay.addLayout(row)
        lay.addStretch(1)
        self.lbl_ver = QLabel("")
        self.lbl_ver.setObjectName("muted")
        lay.addWidget(self.lbl_ver)
        self.b_lock = QPushButton("Bloquear")
        self.b_lock.setObjectName("ghost")
        self.b_lock.setIcon(icon("lock"))
        lay.addWidget(self.b_lock)

    def _go(self, key: str):
        anim.press_scale(self.buttons[key])
        self.navigated.emit(key)

    def set_active(self, key: str):
        b = self.buttons.get(key)
        if b and not b.isChecked():
            b.setChecked(True)

    def set_trash_count(self, n: int):
        self._trash_n = n
        badge = self.badges["trash"]
        if n > 0 and not self._collapsed:
            badge.setText(str(n))
            badge.setVisible(True)
            self.buttons["trash"].setText("Papelera")
        else:
            badge.setVisible(False)
            self.buttons["trash"].setText("" if self._collapsed else "Papelera")

    def set_version(self, v: str):
        self._ver = v
        if not self._collapsed:
            self.lbl_ver.setText(f"v{v}")

    def toggle(self):
        self._collapsed = not self._collapsed
        target = COLLAPSED if self._collapsed else EXPANDED
        anim.collapse_width(self, target, 220)
        if self._collapsed:
            self.brand.setText("A")
            self.brand_icon.setVisible(False)
            self._cap.setVisible(False)
            for b in self.buttons.values():
                b.setText("")
            self.lbl_ver.setText("")
            self.b_lock.setText("")
            self.b_fold.setIcon(icon("chev_r"))
            self.b_fold.setToolTip("Mostrar barra lateral")
            self.set_trash_count(self._trash_n)
        else:
            self.brand.setText("Authenticator")
            self.brand_icon.setVisible(True)
            self._cap.setVisible(True)
            for key, label in (("accounts", "Cuentas"), ("add", "Añadir cuenta"),
                               ("trash", "Papelera"), ("prefs", "Preferencias")):
                self.buttons[key].setText(label)
            self.b_lock.setText("Bloquear")
            self.b_fold.setIcon(icon("chev_l"))
            self.b_fold.setToolTip("Ocultar barra lateral")
            self.set_trash_count(self._trash_n)
            self.set_version(getattr(self, "_ver", "?"))
