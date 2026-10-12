"""Pantalla auth: desbloqueo con backoff 5 intentos. Estilo profesional."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                                QPushButton, QVBoxLayout, QWidget)

from app import auth
from ui.styles import animations as anim
from ui.widgets.icons import icon
from ui.widgets.info import InfoBox


class UnlockScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 36, 32, 36)
        lay.setSpacing(0)
        lay.addStretch(1)
        # Título
        title = QLabel("Desbloquear")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)
        # Info de intentos
        self.info = QLabel("")
        self.info.setObjectName("muted")
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setStyleSheet("font-size: 13px; margin-top: 4px;")
        lay.addWidget(self.info)
        lay.addSpacing(20)
        # Campo de clave
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("Clave maestra")
        self.pw.setStyleSheet("font-size: 16px; padding: 12px 16px;")
        self.pw.returnPressed.connect(self._unlock)
        lay.addWidget(self.pw)
        lay.addSpacing(16)
        # Botón desbloquear
        btn = QPushButton("Desbloquear")
        btn.setObjectName("primary")
        btn.setIcon(icon("lock"))
        btn.setToolTip("Abre la bóveda con tu clave maestra")
        btn.setStyleSheet("font-size: 16px; padding: 14px;")
        btn.clicked.connect(self._unlock)
        lay.addWidget(btn)
        lay.addSpacing(20)
        # InfoBox de recuperación
        lay.addWidget(InfoBox("Si olvidaste la clave, usa tu kit de recuperación offline.", tone="info"))
        lay.addStretch(1)
        # Zona inferior: olvidé la clave + borrar
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.b_kit = QPushButton("Olvidé la clave")
        self.b_kit.setObjectName("ghost")
        self.b_kit.setIcon(icon("key"))
        self.b_kit.setToolTip("Recupera el acceso con tu kit offline")
        self.b_kit.clicked.connect(lambda: self.w.show_recover())
        self.b_wipe = QPushButton("Borrar todo")
        self.b_wipe.setObjectName("danger")
        self.b_wipe.setIcon(icon("trash"))
        self.b_wipe.setToolTip("Borra definitivamente toda la bóveda")
        self.b_wipe.clicked.connect(self._wipe)
        row.addWidget(self.b_kit, 1)
        row.addWidget(self.b_wipe, 1)
        lay.addLayout(row)
        anim.stagger([title, btn])
        self.refresh()

    def refresh(self):
        left = auth.attempts_left()
        d = auth.backoff_delay()
        msg = f"{left} intentos restantes." if left < 5 else ""
        if d > 0:
            msg += f" Espera {int(d)}s."
        self.info.setText(msg)

    def _unlock(self):
        try:
            key = auth.login(self.pw.text())
        except ValueError as e:
            anim.shake(self)
            self.pw.clear()
            self.refresh()
            QMessageBox.warning(self, "Aviso", f"{e} {self.info.text()}")
            return
        self.pw.clear()
        self.w.key = key
        self.w.show_accounts()

    def _wipe(self):
        from app import store, vault
        from ui.widgets.toasts import show_toast
        r = QMessageBox.question(self, "Borrar todo",
                                 "Borra TODA la bóveda de forma definitiva. ¿Continuar?")
        if r != QMessageBox.Yes:
            return
        pw, ok = _ask_password(self)
        if not ok:
            return
        try:
            key = auth.login(pw)
        except ValueError:
            QMessageBox.warning(self, "Aviso", "La clave actual no es correcta.")
            return
        store.wipe_all()
        vault.wipe(key)
        show_toast(self.w, "Bóveda borrada")
        self.w.show_welcome()


def _ask_password(parent):
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
    d = QDialog(parent)
    d.setWindowTitle("Confirmar borrado")
    lay = QVBoxLayout(d)
    edit = QLineEdit()
    edit.setEchoMode(QLineEdit.Password)
    edit.setPlaceholderText("Clave actual")
    lay.addWidget(QLabel("Clave actual:"))
    lay.addWidget(edit)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    lay.addWidget(bb)
    ok = d.exec() == QDialog.Accepted
    return edit.text(), ok
