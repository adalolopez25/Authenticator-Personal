"""Alta compacta: secreto base32 o URI otpauth:// + validacion con codigo esperado."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFormLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from app import store, totp, vault
from ui.styles import animations as anim
from ui.widgets.toasts import show_toast


class AddScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)
        top = QLabel("Añadir cuenta")
        top.setStyleSheet("font-size: 18px; font-weight: 700;")
        lay.addWidget(top)
        form = QFormLayout()
        form.setSpacing(8)
        self.e_issuer = QLineEdit()
        self.e_issuer.setPlaceholderText("Emisor (p. ej. Mi Servicio)")
        self.e_label = QLineEdit()
        self.e_label.setPlaceholderText("Etiqueta (p. ej. usuario@ejemplo.com)")
        self.e_secret = QLineEdit()
        self.e_secret.setPlaceholderText("Secreto base32 o URI otpauth:// completa")
        self.e_secret.textChanged.connect(self._preview)
        self.s_digits = QSpinBox()
        self.s_digits.setRange(6, 8)
        self.s_digits.setValue(6)
        self.s_period = QSpinBox()
        self.s_period.setRange(10, 300)
        self.s_period.setValue(30)
        self.c_algo = QComboBox()
        self.c_algo.addItems(["SHA1", "SHA256", "SHA512"])
        form.addRow("Emisor", self.e_issuer)
        form.addRow("Etiqueta", self.e_label)
        form.addRow("Secreto/URI", self.e_secret)
        form.addRow("Dígitos", self.s_digits)
        form.addRow("Periodo (s)", self.s_period)
        form.addRow("Algoritmo", self.c_algo)
        lay.addLayout(form)
        # Checksum visual: primer codigo esperado (valida sin guardar nada)
        self.lbl_prev = QLabel("Vista previa: —")
        self.lbl_prev.setObjectName("muted")
        self.lbl_prev.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        lay.addWidget(self.lbl_prev)
        hint = QLabel("Sin cámara en MVP: pega el secreto o la URI que da el proveedor.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        row_btns = QVBoxLayout()
        self.b_save = QPushButton("Guardar")
        self.b_save.setObjectName("primary")
        self.b_save.clicked.connect(self._save)
        self.b_back = QPushButton("Volver")
        self.b_back.setObjectName("ghost")
        self.b_back.clicked.connect(lambda: self.w.show_accounts())
        row_btns.addWidget(self.b_save)
        row_btns.addWidget(self.b_back)
        lay.addLayout(row_btns)
        lay.addStretch(1)

    def _preview(self):
        raw = self.e_secret.text().strip()
        if not raw:
            self.lbl_prev.setText("Vista previa: —")
            return
        try:
            if raw.lower().startswith("otpauth://"):
                p = totp.parse_uri(raw)
                self.e_issuer.setText(p["issuer"] or self.e_issuer.text())
                self.e_label.setText(p["label"] or self.e_label.text())
                self.s_digits.setValue(p["digits"])
                self.s_period.setValue(p["period"])
                self.c_algo.setCurrentText(p["algo"].upper())
                import base64 as _b
                sec = _b.b32decode(p["secret_b32"] + "=" * (-len(p["secret_b32"]) % 8))
                code = totp.generate(sec, digits=p["digits"], period=p["period"], algo=p["algo"])
            else:
                p = totp.parse_any(raw)
                import base64 as _b
                sec = _b.b32decode(p["secret_b32"] + "=" * (-len(p["secret_b32"]) % 8))
                code = totp.generate(sec, digits=self.s_digits.value(),
                                      period=self.s_period.value(),
                                      algo=self.c_algo.currentText())
            self.lbl_prev.setText(f"Código esperado ahora: {code}  (verifícalo con el proveedor)")
        except ValueError:
            self.lbl_prev.setText("Secreto inválido: revisa el base32 o la URI.")

    def _save(self):
        key = self.w.key
        if key is None:
            return
        raw = self.e_secret.text().strip()
        try:
            if raw.lower().startswith("otpauth://"):
                p = totp.parse_uri(raw)
                issuer = self.e_issuer.text().strip() or p["issuer"] or "Mi Servicio"
                label = self.e_label.text().strip() or p["label"] or "Cuenta"
            else:
                p0 = totp.parse_any(raw)
                p = {"secret_b32": p0["secret_b32"], "digits": self.s_digits.value(),
                     "period": self.s_period.value(),
                     "algo": self.c_algo.currentText().lower().replace("-", "")}
                issuer = self.e_issuer.text().strip() or "Mi Servicio"
                label = self.e_label.text().strip() or "Cuenta"
        except ValueError as e:
            anim.shake(self)
            QMessageBox.warning(self, "Aviso", str(e))
            return
        packed = store.pack_secret(p["secret_b32"], p["digits"], p["period"], p["algo"])
        blobs = {"issuer": vault.encrypt(key, issuer.encode()),
                 "label": vault.encrypt(key, label.encode()),
                 "secret": vault.encrypt(key, packed.encode())}
        store.create_account(blobs)
        self.e_secret.clear()
        show_toast(self.w, "Cuenta guardada (cifrada)")
        self.w.show_accounts()
