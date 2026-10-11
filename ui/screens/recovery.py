"""Pantalla auth: kit offline (mostrar una vez / usar / rotar)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel, QLineEdit, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from app import auth
from ui.widgets.toasts import show_toast


class KitScreen(QWidget):
    """Modo mostrar (first_time con confirmacion) o modo recuperar."""

    def __init__(self, window, code: str = "", first_time: bool = False,
                 recover_mode: bool = False):
        super().__init__()
        self.w = window
        self.code = code
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(10)
        if recover_mode:
            title = QLabel("Recuperar con kit")
            lay.addWidget(title)
            info = QLabel("Pega tu kit offline y fija una clave nueva. Se emitirá un kit fresco.")
            info.setObjectName("muted")
            info.setWordWrap(True)
            lay.addWidget(info)
            self.kit = QLineEdit()
            self.kit.setPlaceholderText("Código del kit (grupos de 5)")
            self.n1 = QLineEdit()
            self.n1.setEchoMode(QLineEdit.Password)
            self.n1.setPlaceholderText("Nueva clave maestra")
            self.n2 = QLineEdit()
            self.n2.setEchoMode(QLineEdit.Password)
            self.n2.setPlaceholderText("Repite la nueva clave")
            for e in (self.kit, self.n1, self.n2):
                lay.addWidget(e)
            b = QPushButton("Recuperar y entrar")
            b.setObjectName("primary")
            b.clicked.connect(self._recover)
            lay.addWidget(b)
        else:
            title = QLabel("Kit de recuperación")
            title.setStyleSheet("font-size: 20px; font-weight: 700;")
            lay.addWidget(title)
            info = QLabel("Guárdalo en papel, fuera del PC. Se muestra UNA sola vez. "
                          "Sin él, perder el PC = perder el 2FA.")
            info.setObjectName("muted")
            info.setWordWrap(True)
            lay.addWidget(info)
            box = QLabel(code or "")
            box.setWordWrap(True)
            box.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            box.setStyleSheet("font-family: Consolas; font-size: 14px; letter-spacing: 1px;")
            lay.addWidget(box)
            b = QPushButton("Ya lo guardé, entrar" if first_time else "Cerrar")
            b.setObjectName("primary")
            b.clicked.connect(self.w.show_accounts)
            lay.addWidget(b)
            if not first_time:
                lay.addWidget(QLabel("Rotar el kit invalida el anterior."))
                r = QPushButton("Rotar kit (pide clave)")
                r.setObjectName("ghost")
                r.clicked.connect(self._rotate)
                lay.addWidget(r)
        lay.addStretch(1)

    def _recover(self):
        if self.n1.text() != self.n2.text():
            QMessageBox.warning(self, "Aviso", "Las claves nuevas no coinciden.")
            return
        try:
            key, fresh = auth.recover_with_kit(self.kit.text(), self.n1.text())
        except ValueError as e:
            QMessageBox.warning(self, "Aviso", str(e))
            return
        self.w.key = key
        show_toast(self.w, "Recuperado: guarda tu nuevo kit")
        self.w.show_kit(fresh, first_time=True)

    def _rotate(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        d = QDialog(self)
        d.setWindowTitle("Rotar kit")
        lay = QVBoxLayout(d)
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.Password)
        pw.setPlaceholderText("Clave actual")
        lay.addWidget(QLabel("Escribe tu clave actual:"))
        lay.addWidget(pw)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        if d.exec() != QDialog.Accepted:
            return
        try:
            code = auth.rotate_recovery(pw.text())
        except ValueError as e:
            QMessageBox.warning(self, "Aviso", str(e))
            return
        self.w.show_kit(code, first_time=True)
