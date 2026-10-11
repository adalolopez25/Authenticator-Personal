"""Pantalla auth: crear boveda (primer arranque). Tarjeta compacta."""
from __future__ import annotations

from PySide6.QtWidgets import (QFormLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from app import auth
from ui.styles import animations as anim
from ui.widgets.toasts import show_toast


class WelcomeScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(10)
        title = QLabel("Authenticator")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        lay.addWidget(title)
        sub = QLabel("Crea tu bóveda local. Sin cuentas, sin nube.")
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        form = QFormLayout()
        form.setSpacing(8)
        self.user = QLineEdit()
        self.user.setPlaceholderText("Usuario local (p. ej. yo)")
        self.p1 = QLineEdit()
        self.p1.setEchoMode(QLineEdit.Password)
        self.p1.setPlaceholderText("Clave maestra (12+, 3 de 4 clases)")
        self.p2 = QLineEdit()
        self.p2.setEchoMode(QLineEdit.Password)
        self.p2.setPlaceholderText("Repite la clave maestra")
        form.addRow("Usuario", self.user)
        form.addRow("Clave", self.p1)
        form.addRow("Repetir", self.p2)
        lay.addLayout(form)
        hint = QLabel("Guarda los códigos de respaldo de cada proveedor en papel.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        btn = QPushButton("Crear bóveda")
        btn.setObjectName("primary")
        btn.clicked.connect(self._create)
        lay.addWidget(btn)
        lay.addStretch(1)
        anim.stagger([title, sub, btn])

    def _create(self):
        user = self.user.text().strip() or "yo"
        if self.p1.text() != self.p2.text():
            anim.shake(self)
            QMessageBox.warning(self, "Aviso", "Las claves no coinciden.")
            return
        try:
            key, code = auth.create_master(user, self.p1.text())
        except ValueError as e:
            anim.shake(self)
            QMessageBox.warning(self, "Aviso", str(e))
            return
        self.w.key = key
        show_toast(self.w, "Bóveda creada")
        self.w.show_kit(code, first_time=True)
