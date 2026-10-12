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
        self._host = None  # lo fija open_add_modal para poder cerrarse
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)
        # Tarjeta de formulario (el modal aporta el header con X)
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
        self.s_digits = QComboBox()
        self.s_digits.addItems(["6", "7", "8"])
        self.s_digits.setCurrentText("6")
        self.s_digits.setToolTip("Número dígitos del código (6–8)")
        self.s_period = QComboBox()
        self.s_period.addItems(["10", "15", "30", "60", "90", "120", "180", "300"])
        self.s_period.setCurrentText("30")
        self.s_period.setToolTip("Segundos que dura cada código")
        self.s_digits.currentTextChanged.connect(lambda: self._preview())
        self.s_period.currentTextChanged.connect(lambda: self._preview())
        self.c_algo = QComboBox()
        self.c_algo.addItems(["SHA1", "SHA256", "SHA512"])
        self.c_algo.currentTextChanged.connect(lambda: self._preview())
        form.addRow("Emisor", self.e_issuer)
        form.addRow("Etiqueta", self.e_label)
        form.addRow("Secreto / URI", self.e_secret)
        row_opt = QHBoxLayout()
        row_opt.setContentsMargins(0, 0, 0, 0)
        row_opt.setSpacing(8)
        for lab, wid, tip in (
            ("Dígitos", self.s_digits, "Número de dígitos del código TOTP.\nEstándar: 6 dígitos.\nAlgunos servicios usan 7 u 8."),
            ("Periodo (s)", self.s_period, "Segundos que dura cada código.\nEstándar: 30 segundos.\nAlgunos servicios usan 60 o más."),
            ("Algoritmo", self.c_algo, "Algoritmo de hash del TOTP.\nEstándar: SHA1.\nSHA256/SHA512 son más seguros."),
        ):
            cell = QVBoxLayout()
            cell.setContentsMargins(0, 0, 0, 0)
            cell.setSpacing(4)
            l = QLabel(lab)
            l.setObjectName("muted")
            cell.addWidget(l)
            hbox = QHBoxLayout()
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(4)
            hbox.addWidget(wid, 1)
            btn_help = QPushButton()
            btn_help.setObjectName("iconBtn")
            btn_help.setIcon(icon("question"))
            btn_help.setFixedSize(24, 24)
            btn_help.setToolTip(tip)
            btn_help.clicked.connect(lambda checked=False, t=tip: QMessageBox.information(self, "Ayuda", t))
            hbox.addWidget(btn_help)
            cell.addLayout(hbox)
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
        self.b_back = QPushButton("Cancelar")
        self.b_back.setObjectName("ghost")
        self.b_back.setIcon(icon("chev_l"))
        self.b_back.setToolTip("Cerrar sin guardar")
        self.b_back.clicked.connect(self._close_host)
        self.b_save = QPushButton("Guardar cuenta")
        self.b_save.setObjectName("primary")
        self.b_save.setIcon(icon("check"))
        self.b_save.setToolTip("Cifra y guarda la cuenta nueva")
        self.b_save.clicked.connect(self._save)
        btns.addWidget(self.b_back, 1)
        btns.addWidget(self.b_save, 2)
        lay.addLayout(btns)
        anim.stagger([card, prev])

    def _close_host(self):
        try:
            if self._host is not None:
                self._host.reject()
        except (RuntimeError, Exception):
            pass

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
                self.s_digits.setCurrentText(str(p["digits"]))
                self.s_period.setCurrentText(str(p["period"]))
                self.c_algo.setCurrentText(p["algo"].upper())
                import base64 as _b
                sec = _b.b32decode(p["secret_b32"] + "=" * (-len(p["secret_b32"]) % 8))
                code = totp.generate(sec, digits=p["digits"], period=p["period"], algo=p["algo"])
            else:
                p = totp.parse_any(raw)
                import base64 as _b
                sec = _b.b32decode(p["secret_b32"] + "=" * (-len(p["secret_b32"]) % 8))
                code = totp.generate(sec, digits=int(self.s_digits.currentText()),
                                      period=int(self.s_period.currentText()),
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
                p = {"secret_b32": p0["secret_b32"], "digits": int(self.s_digits.currentText()),
                     "period": int(self.s_period.currentText()),
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
        self._close_host()
        self.w.show_accounts()


def open_add_modal(window) -> None:
    """Añadir cuenta en modal centrado (bloqueante, con X)."""
    from PySide6.QtCore import QRect, QTimer
    from PySide6.QtWidgets import QHBoxLayout as _HL
    from ui.styles import animations as _anim
    from ui.widgets.icons import icon as _icon
    from ui.widgets.modal import ModalHost

    host = ModalHost(window)
    host.card.setMinimumSize(680, 560)
    host.card.setMaximumSize(780, 680)
    lay = QVBoxLayout(host.card)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(10)
    head = _HL()
    head.setContentsMargins(0, 0, 0, 0)
    title = QLabel("Añadir cuenta")
    title.setStyleSheet("font-size: 20px; font-weight: 700;")
    head.addWidget(title, 1)
    b_x = QPushButton()
    b_x.setObjectName("iconBtn")
    b_x.setIcon(_icon("x"))
    b_x.setToolTip("Cerrar sin guardar")
    b_x.setFixedSize(36, 36)
    b_x.clicked.connect(host.reject)
    head.addWidget(b_x)
    lay.addLayout(head)
    form = AddScreen(window)
    form._host = host
    lay.addWidget(form, 1)
    try:
        top = window.mapToGlobal(window.rect().topLeft())
        host.setGeometry(QRect(top, window.size()))
    except Exception:
        pass
    QTimer.singleShot(60, lambda: _anim.fade_in(host.card, 200))
    try:
        host.exec()
    finally:
        host.deleteLater()
