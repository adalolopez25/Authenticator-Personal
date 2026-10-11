"""Alta de cuenta: tarjeta de formulario + vista previa en vivo del codigo."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from app import store, totp, vault
from ui.styles import animations as anim
from ui.widgets.icons import icon
from ui.widgets.toasts import show_toast


class AddScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        # Header con icono
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(12)
        badge = QLabel()
        badge.setObjectName("authIcon")
        badge.setPixmap(icon("plus").pixmap(28, 28))
        badge.setFixedSize(56, 56)
        badge.setAlignment(Qt.AlignCenter)
        head.addWidget(badge)
        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        t = QLabel("Añadir cuenta")
        t.setStyleSheet("font-size: 22px; font-weight: 700;")
        titles.addWidget(t)
        s = QLabel("Pega el secreto o la URI otpauth:// del proveedor")
        s.setObjectName("muted")
        titles.addWidget(s)
        head.addLayout(titles, 1)
        lay.addLayout(head)
        # Tarjeta de formulario
        card = QWidget()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        self.e_issuer = QLineEdit()
        self.e_issuer.setPlaceholderText("Emisor (p. ej. Mi Servicio)")
        self.e_issuer.setClearButtonEnabled(True)
        self.e_label = QLineEdit()
        self.e_label.setPlaceholderText("Etiqueta (p. ej. usuario@ejemplo.com)")
        self.e_label.setClearButtonEnabled(True)
        self.e_secret = QLineEdit()
        self.e_secret.setPlaceholderText("Secreto base32 o URI otpauth:// completa")
        self.e_secret.setClearButtonEnabled(True)
        self.e_secret.textChanged.connect(self._preview)
        self.s_digits = QSpinBox()
        self.s_digits.setRange(6, 8)
        self.s_digits.setValue(6)
        self.s_period = QSpinBox()
        self.s_period.setRange(10, 300)
        self.s_period.setValue(30)
        self.s_digits.valueChanged.connect(lambda: self._preview())
        self.s_period.valueChanged.connect(lambda: self._preview())
        self.c_algo = QComboBox()
        self.c_algo.addItems(["SHA1", "SHA256", "SHA512"])
        self.c_algo.currentTextChanged.connect(lambda: self._preview())
        form.addRow("Emisor", self.e_issuer)
        form.addRow("Etiqueta", self.e_label)
        form.addRow("Secreto / URI", self.e_secret)
        row_opt = QHBoxLayout()
        row_opt.setContentsMargins(0, 0, 0, 0)
        row_opt.setSpacing(8)
        for lab, wid in (("Dígitos", self.s_digits), ("Periodo (s)", self.s_period),
                         ("Algoritmo", self.c_algo)):
            cell = QVBoxLayout()
            cell.setContentsMargins(0, 0, 0, 0)
            cell.setSpacing(4)
            l = QLabel(lab)
            l.setObjectName("muted")
            cell.addWidget(l)
            cell.addWidget(wid)
            row_opt.addLayout(cell, 1)
        cl.addLayout(form)
        cl.addLayout(row_opt)
        lay.addWidget(card)
        # Vista previa en vivo (checksum visual)
        prev = QWidget()
        prev.setObjectName("previewCard")
        pl = QHBoxLayout(prev)
        pl.setContentsMargins(18, 14, 18, 14)
        pl.setSpacing(12)
        ptxt = QVBoxLayout()
        ptxt.setContentsMargins(0, 0, 0, 0)
        ptxt.setSpacing(2)
        l1 = QLabel("CÓDIGO ESPERADO AHORA")
        l1.setObjectName("muted")
        ptxt.addWidget(l1)
        self.lbl_code = QLabel("— — —")
        self.lbl_code.setObjectName("previewCode")
        ptxt.addWidget(self.lbl_code)
        self.lbl_hint = QLabel("Escríbelo en el proveedor para verificar")
        self.lbl_hint.setObjectName("muted")
        self.lbl_hint.setWordWrap(True)
        ptxt.addWidget(self.lbl_hint)
        pl.addLayout(ptxt, 1)
        self.lbl_state = QLabel()
        self.lbl_state.setPixmap(icon("shield").pixmap(40, 40))
        pl.addWidget(self.lbl_state)
        lay.addWidget(prev)
        # Acciones lado a lado
        btns = QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(10)
        self.b_back = QPushButton("Volver")
        self.b_back.setObjectName("ghost")
        self.b_back.setIcon(icon("chev_l"))
        self.b_back.clicked.connect(lambda: self.w.show_accounts())
        self.b_save = QPushButton("Guardar cuenta")
        self.b_save.setObjectName("primary")
        self.b_save.setIcon(icon("check"))
        self.b_save.clicked.connect(self._save)
        btns.addWidget(self.b_back, 1)
        btns.addWidget(self.b_save, 2)
        lay.addLayout(btns)
        lay.addStretch(1)
        anim.stagger([card, prev])

    def _preview(self):
        raw = self.e_secret.text().strip()
        if not raw:
            self.lbl_code.setText("— — —")
            self.lbl_hint.setText("Escríbelo en el proveedor para verificar")
            self.lbl_state.setPixmap(icon("shield").pixmap(40, 40))
            return
        try:
            if raw.lower().startswith("otpauth://"):
                p = totp.parse_uri(raw)
                if not self.e_issuer.text().strip() and p["issuer"]:
                    self.e_issuer.setText(p["issuer"])
                if not self.e_label.text().strip() and p["label"]:
                    self.e_label.setText(p["label"])
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
            self.lbl_code.setText(f"{code[:len(code) // 2]} {code[len(code) // 2:]}")
            self.lbl_hint.setText("Coincide con tu proveedor: es válido. Guárdalo.")
            self.lbl_state.setPixmap(icon("check").pixmap(40, 40))
        except ValueError:
            self.lbl_code.setText("— — —")
            self.lbl_hint.setText("Secreto inválido: revisa el base32 o la URI.")
            self.lbl_state.setPixmap(icon("alert").pixmap(40, 40))

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
