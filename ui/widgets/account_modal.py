"""Modal de cuenta: UN solo codigo en vivo + acciones. Se abre al pulsar un mosaico."""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QProgressBar,
                               QPushButton, QVBoxLayout, QWidget)

from app import settings, totp
from app.utils import clipboard_history_on, copy_and_clear
from ui.styles import animations as anim
from ui.widgets.icons import icon
from ui.widgets.issuer import art_label
from ui.widgets.modal import ModalHost
from ui.widgets.toasts import show_toast


class AccountModal(QWidget):
    def __init__(self, host: ModalHost, window, acc_id: str):
        super().__init__()
        self.host = host
        self.w = window
        self.acc_id = acc_id
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)
        # Header: monograma + nombres + X
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(12)
        self._head = head
        self.art = art_label("", "", 64)
        head.addWidget(self.art)
        names = QVBoxLayout()
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(2)
        self.lbl_issuer = QLabel("")
        self.lbl_issuer.setStyleSheet("font-size: 18px; font-weight: 700;")
        names.addWidget(self.lbl_issuer)
        self.lbl_label = QLabel("")
        self.lbl_label.setObjectName("muted")
        names.addWidget(self.lbl_label)
        head.addLayout(names, 1)
        b_x = QPushButton()
        b_x.setObjectName("iconBtn")
        b_x.setIcon(icon("x"))
        b_x.setToolTip("Cerrar")
        b_x.setFixedSize(36, 36)
        b_x.clicked.connect(host.reject)
        head.addWidget(b_x, 0, Qt.AlignTop)
        lay.addLayout(head)
        # Tarjeta del codigo (el UNICO visible)
        code_card = QWidget()
        code_card.setObjectName("previewCard")
        cl = QVBoxLayout(code_card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(8)
        cap = QLabel("CÓDIGO ACTUAL")
        cap.setObjectName("muted")
        cl.addWidget(cap)
        self.lbl_code = QLabel("··· ···")
        self.lbl_code.setObjectName("modalCode")
        self.lbl_code.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.lbl_code)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.bar = QProgressBar()
        self.bar.setObjectName("count")
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        row.addWidget(self.bar, 1)
        self.lbl_remain = QLabel("")
        self.lbl_remain.setObjectName("remain")
        row.addWidget(self.lbl_remain)
        cl.addLayout(row)
        lay.addWidget(code_card)
        # Copiar
        self.b_copy = QPushButton("Copiar código")
        self.b_copy.setObjectName("primary")
        self.b_copy.setIcon(icon("copy"))
        self.b_copy.setToolTip("Copia el código actual")
        self.b_copy.clicked.connect(self._copy)
        lay.addWidget(self.b_copy)
        # Acciones segun modo
        trash = self._is_trash()
        grid = QHBoxLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        if trash:
            b_res = QPushButton("Restaurar")
            b_res.setObjectName("ghost")
            b_res.setIcon(icon("refresh"))
            b_res.setToolTip("Devuelve la cuenta a la lista")
            b_res.clicked.connect(self._restore)
            b_del = QPushButton("Eliminar definitivo")
            b_del.setObjectName("danger")
            b_del.setIcon(icon("trash"))
            b_del.setToolTip("Borra para siempre, sin vuelta atrás")
            b_del.clicked.connect(self._hard_delete)
            grid.addWidget(b_res, 1)
            grid.addWidget(b_del, 1)
        else:
            for label, ic, tip, fn in (
                    ("Renombrar", "edit", "Cambia emisor o etiqueta", self._rename),
                    ("Subir", "up", "Mueve la cuenta hacia arriba", lambda: self._move(-1)),
                    ("Bajar", "down", "Mueve la cuenta hacia abajo", lambda: self._move(1))):
                b = QPushButton(label)
                b.setObjectName("ghost")
                b.setIcon(icon(ic))
                b.setToolTip(tip)
                b.clicked.connect(fn)
                grid.addWidget(b, 1)
        lay.addLayout(grid)
        if not trash:
            b_del = QPushButton("Eliminar")
            b_del.setObjectName("danger")
            b_del.setIcon(icon("trash"))
            b_del.setToolTip("Mueve la cuenta a la papelera")
            b_del.clicked.connect(self._delete)
            lay.addWidget(b_del)
        self._refresh_header()
        self._tick()
        anim.fade_in(self, 200)
        # Vivo mientras esta abierto: refresca cada segundo.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    # ---- datos ----
    def _entry(self) -> dict | None:
        try:
            scr = getattr(self.w, "scr", None)
            if scr is None or self.w.key is None:
                return None
            return scr.cache.get(self.acc_id)
        except (RuntimeError, AttributeError):
            return None

    def _is_trash(self) -> bool:
        try:
            return bool(getattr(self.w.scr, "trash_mode", False))
        except (RuntimeError, AttributeError):
            return False

    def _refresh_header(self):
        d = self._entry()
        if not d:
            return
        iss, lab = d["issuer"], d["label"]
        try:
            fresh = art_label(iss, lab, 64)
            old = self.art
            self.art = fresh
            self._head.replaceWidget(old, fresh)
            old.deleteLater()
        except RuntimeError:
            pass
        self.lbl_issuer.setText(iss or lab or "Cuenta")
        self.lbl_label.setText(lab if iss else "")

    def _tick(self):
        d = self._entry()
        if not d:
            self.host.reject()  # bloqueada o eliminada: cerrar
            return
        try:
            self.w._last_active = time.time()
            code = totp.generate(d["secret"], digits=d["digits"],
                                 period=d["period"], algo=d["algo"])
            remain = totp.seconds_remaining(period=d["period"])
            self.lbl_code.setText(f"{code[:len(code) // 2]} {code[len(code) // 2:]}")
            self.bar.setRange(0, max(1, d["period"]))
            self.bar.setValue(max(0, remain))
            self.lbl_remain.setText(f"{remain}s")
            urgent = remain <= 5
            for wid in (self.bar, self.lbl_remain):
                if wid.property("urgent") != urgent:
                    wid.setProperty("urgent", urgent)
                    wid.style().unpolish(wid)
                    wid.style().polish(wid)
        except (ValueError, RuntimeError):
            pass

    # ---- acciones ----
    def _copy(self):
        try:
            self.w.scr.copy_code(self.acc_id)
        except (RuntimeError, AttributeError):
            pass

    def _rename(self):
        try:
            self.w.scr._rename(self.acc_id)
            self._refresh_header()
        except (RuntimeError, AttributeError):
            pass

    def _move(self, delta: int):
        try:
            self.w.scr._move(self.acc_id, delta)
        except (RuntimeError, AttributeError):
            pass

    def _delete(self):
        try:
            self.w.scr._soft_delete(self.acc_id)
        except (RuntimeError, AttributeError):
            pass
        self.host.accept()

    def _restore(self):
        try:
            self.w.scr._restore(self.acc_id)
        except (RuntimeError, AttributeError):
            pass
        self.host.accept()

    def _hard_delete(self):
        r = QMessageBox.question(self, "Eliminar",
                                 "Eliminación definitiva, sin vuelta atrás. ¿Continuar?")
        if r != QMessageBox.Yes:
            return
        try:
            from app import store
            store.hard_delete_account(self.acc_id)
            self.w.scr.reload(keep_codes=True)
        except (RuntimeError, AttributeError):
            pass
        self.host.accept()


def open_account_modal(window, acc_id: str) -> None:
    """Abre el modal del codigo unico (bloqueante, centrado)."""
    from PySide6.QtCore import QRect, QTimer
    host = ModalHost(window)
    host.card.setMinimumWidth(400)
    host.card.setMaximumWidth(460)
    lay = QVBoxLayout(host.card)
    lay.setContentsMargins(20, 18, 20, 18)
    lay.addWidget(AccountModal(host, window, acc_id))
    try:
        top = window.mapToGlobal(window.rect().topLeft())
        host.setGeometry(QRect(top, window.size()))
    except Exception:
        pass
    QTimer.singleShot(60, lambda: anim.fade_in(host.card, 200))
    try:
        host.exec()
    finally:
        host.deleteLater()
