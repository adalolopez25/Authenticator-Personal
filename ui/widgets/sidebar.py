"""Sidebar de navegacion (solo modo escritorio/app). Colapsable con animacion."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from ui.styles import animations as anim
from ui.widgets.icons import icon

EXPANDED = 248
COLLAPSED = 68


class Sidebar(QWidget):
    navigated = Signal(str)  # accounts | add | trash | prefs

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(EXPANDED)
        self._collapsed = False
        self._trash_n = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(4)
        brand = QLabel("Authenticator")
        brand.setObjectName("brand")
        lay.addWidget(brand)
        self._brand = brand
        lay.addSpacing(8)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        self.badges: dict[str, QLabel] = {}
        for key, label, ic in (("accounts", "Cuentas", "key"),
                               ("add", "Añadir cuenta", "plus"),
                               ("trash", "Papelera", "trash"),
                               ("prefs", "Preferencias", "gear")):
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
            setattr(self, f"_row_{key}", row)
        lay.addStretch(1)
        self.lbl_ver = QLabel("")
        self.lbl_ver.setObjectName("muted")
        lay.addWidget(self.lbl_ver)
        bottom = QHBoxLayout()
        self.b_lock = QPushButton("Bloquear")
        self.b_lock.setObjectName("ghost")
        self.b_lock.setIcon(icon("lock"))
        bottom.addWidget(self.b_lock, 1)
        self.b_fold = QPushButton("«")
        self.b_fold.setObjectName("toolBtn")
        self.b_fold.setToolTip("Colapsar barra")
        self.b_fold.setFixedWidth(36)
        self.b_fold.clicked.connect(self.toggle)
        bottom.addWidget(self.b_fold)
        lay.addLayout(bottom)

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
        self.lbl_ver.setText(f"v{v}")

    def toggle(self):
        self._collapsed = not self._collapsed
        target = COLLAPSED if self._collapsed else EXPANDED
        anim.collapse_width(self, target, 220)
        if self._collapsed:
            for key, b in self.buttons.items():
                b.setText("")
            self.lbl_ver.setText("")
            self._brand.setText("A")
            self.b_lock.setText("")
            self.b_fold.setText("»")
            self.set_trash_count(self._trash_n)
        else:
            for key, label in (("accounts", "Cuentas"), ("add", "Añadir cuenta"),
                               ("trash", "Papelera"), ("prefs", "Preferencias")):
                self.buttons[key].setText(label)
            self._brand.setText("Authenticator")
            self.b_lock.setText("Bloquear")
            self.b_fold.setText("«")
            self.set_trash_count(self._trash_n)
