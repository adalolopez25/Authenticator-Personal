"""Pantalla auth: desbloqueo con backoff 5 intentos."""
from __future__ import annotations

from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from app import auth
from ui.styles import animations as anim


class UnlockScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(10)
        title = QLabel("Desbloquear")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        lay.addWidget(title)
        self.info = QLabel("")
        self.info.setObjectName("muted")
        lay.addWidget(self.info)
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("Clave maestra")
        self.pw.returnPressed.connect(self._unlock)
        lay.addWidget(self.pw)
        btn = QPushButton("Desbloquear")
        btn.setObjectName("primary")
        btn.clicked.connect(self._unlock)
        lay.addWidget(btn)
        row = QHBoxLayout()
        self.b_kit = QPushButton("Olvidé la clave (kit)")
        self.b_kit.setObjectName("ghost")
        self.b_kit.clicked.connect(lambda: self.w.show_recover())
        self.b_wipe = QPushButton("Borrar todo")
        self.b_wipe.setObjectName("danger")
        self.b_wipe.clicked.connect(self._wipe)
        row.addWidget(self.b_kit, 1)
        row.addWidget(self.b_wipe, 1)
        lay.addLayout(row)
        lay.addStretch(1)
        anim.stagger([title, btn])
        self.refresh()

    def refresh(self):
        left = auth.attempts_left()
        d = auth.backoff_delay()
        msg = f"Intentos restantes: {left}." if left < 5 else ""
        if d > 0:
            msg += f" Espera {int(d)}s antes de intentar."
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
                                 "Borra TODA la bóveda. Escribe la clave actual en Desbloquear "
                                 "antes, o usa el kit. ¿Continuar al borrado total?")
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
    lay.addWidget(QLabel("Escribe tu clave actual para borrar todo:"))
    lay.addWidget(edit)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    lay.addWidget(bb)
    ok = d.exec() == QDialog.Accepted
    return edit.text(), ok
