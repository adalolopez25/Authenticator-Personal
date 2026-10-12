"""Sidebar de navegacion (solo modo escritorio/app). Colapsable con animacion.

Nav: Cuentas + Papelera. Preferencias vive abajo, justo encima de Bloquear.
El colapso intercambia textos a mitad de la animacion (fluido, sin salto).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from ui.styles import animations as anim
from ui.widgets.icons import icon

EXPANDED = 252
COLLAPSED = 72
COLLAPSE_MS = 240


class Sidebar(QWidget):
    navigated = Signal(str)  # accounts | trash | prefs

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
                               ("trash", "Papelera", "trash")):
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
        # Preferencias arriba de Bloquear: mismo estilo fantasma centrado.
        self.b_prefs = QPushButton("Preferencias")
        self.b_prefs.setObjectName("ghost")
        self.b_prefs.setIcon(icon("sliders"))
        self.b_prefs.setToolTip("Abrir preferencias")
        self.b_prefs.clicked.connect(lambda: self._go("prefs"))
        lay.addWidget(self.b_prefs)
        self.lbl_ver = QLabel("")
        self.lbl_ver.setObjectName("muted")
        self.lbl_ver.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_ver)
        self.b_lock = QPushButton("Bloquear")
        self.b_lock.setObjectName("ghost")
        self.b_lock.setIcon(icon("lock"))
        self.b_lock.setToolTip("Bloquea la app ahora")
        lay.addWidget(self.b_lock)

    def _go(self, key: str):
        if key in self.buttons:
            anim.press_scale(self.buttons[key])
        else:
            anim.press_scale(self.b_prefs)
        self.navigated.emit(key)

    def set_active(self, key: str):
        if key == "prefs":
            return  # el modal no cambia de pagina: se conserva la anterior
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
        anim.collapse_width(self, target, COLLAPSE_MS)
        # Swap de textos a mitad de la animacion: queda enmascarado por el
        # movimiento y se percibe fluido en vez de un salto seco.
        QTimer.singleShot(COLLAPSE_MS // 2, self._apply_collapsed_text)
        self.b_fold.setIcon(icon("chev_r" if self._collapsed else "chev_l"))
        self.b_fold.setToolTip("Mostrar barra lateral" if self._collapsed
                               else "Ocultar barra lateral")

    def _apply_collapsed_text(self):
        try:
            if self._collapsed:
                self.brand.setText("")
                self.brand_icon.setVisible(False)
                self._cap.setVisible(False)
                for b in self.buttons.values():
                    b.setText("")
                self.b_prefs.setText("")
                self.lbl_ver.setText("")
                self.b_lock.setText("")
                self.set_trash_count(self._trash_n)
            else:
                self.brand.setText("Authenticator")
                self.brand_icon.setVisible(True)
                self._cap.setVisible(True)
                for key, label in (("accounts", "Cuentas"), ("trash", "Papelera")):
                    self.buttons[key].setText(label)
                self.b_prefs.setText("Preferencias")
                self.b_lock.setText("Bloquear")
                self.set_trash_count(self._trash_n)
                self.set_version(getattr(self, "_ver", "?"))
        except RuntimeError:
            pass
