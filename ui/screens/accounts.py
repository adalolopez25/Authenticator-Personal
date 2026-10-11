"""Vista principal compacta: columna unica, codigo grande + countdown + clic-para-copiar."""
from __future__ import annotations

import base64
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from app import settings, store, totp, vault
from app.utils import copy_and_clear
from ui.styles import animations as anim
from ui.widgets.icons import icon
from ui.widgets.toasts import show_toast


class AccountRow(QWidget):
    def __init__(self, parent_list, acc_id: str, issuer: str, label: str,
                 code: str, remain: int, period: int, trash_mode: bool = False):
        super().__init__()
        self.L = parent_list
        self.acc_id = acc_id
        self.setObjectName("row")
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        top = QHBoxLayout()
        name = QLabel(f"{issuer} · {label}" if issuer and label else (issuer or label or "Cuenta"))
        name.setObjectName("issuer")
        top.addWidget(name, 1)
        self.b_menu = QPushButton("⋮")
        self.b_menu.setObjectName("toolBtn")
        self.b_menu.setFixedWidth(30)
        self.b_menu.clicked.connect(lambda: self.L.row_menu(self.acc_id, self.b_menu))
        top.addWidget(self.b_menu)
        lay.addLayout(top)
        self.lbl_code = QLabel(f"{code[:len(code)//2]} {code[len(code)//2:]}" if len(code) > 4 else code)
        self.lbl_code.setObjectName("code")
        lay.addWidget(self.lbl_code)
        self.bar = QProgressBar()
        self.bar.setObjectName("count")
        self.bar.setRange(0, max(1, period))
        self.bar.setValue(max(0, remain))
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        lay.addWidget(self.bar)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.L.copy_code(self.acc_id)
        super().mousePressEvent(event)

    def refresh(self, code: str, remain: int):
        self.lbl_code.setText(f"{code[:len(code)//2]} {code[len(code)//2:]}" if len(code) > 4 else code)
        self.bar.setValue(max(0, remain))


class AccountsScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        self.trash_mode = False
        self.cache: dict[str, dict] = {}  # acc_id -> {issuer,label,secret,digits,period,algo}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)
        # Buscador
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Buscar cuenta…")
        self.search.textChanged.connect(lambda: self.reload(keep_codes=True))
        lay.addWidget(self.search)
        # Barra papelera + conteo
        mid = QHBoxLayout()
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("muted")
        mid.addWidget(self.lbl_count, 1)
        self.b_trash = QPushButton("Papelera")
        self.b_trash.setObjectName("ghost")
        self.b_trash.setCheckable(True)
        self.b_trash.clicked.connect(self._toggle_trash)
        mid.addWidget(self.b_trash)
        lay.addLayout(mid)
        # Lista scrolleable
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.inner = QWidget()
        self.vbox = QVBoxLayout(self.inner)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(8)
        self.vbox.addStretch(1)
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll, 1)
        # Barra + Añadir
        self.b_add = QPushButton("+ Añadir")
        self.b_add.setObjectName("primary")
        self.b_add.setIcon(icon("plus"))
        self.b_add.clicked.connect(lambda: self.w.show_add())
        lay.addWidget(self.b_add)
        # Refresco por QTimer (1s): recalcula codigos + countdown
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    # ---- datos ----
    def reload(self, keep_codes: bool = False):
        key = self.w.key
        if key is None:
            return
        rows = store.list_accounts_meta(
            include_deleted=self.trash_mode, deleted_only=self.trash_mode)
        self.cache.clear()
        for r in rows:
            try:
                iss = vault.decrypt(key, r.get("issuer_blob", "")).decode("utf-8") if r.get("issuer_blob") else ""
                lab = vault.decrypt(key, r.get("label_blob", "")).decode("utf-8") if r.get("label_blob") else ""
                sec_raw = vault.decrypt(key, r.get("secret_blob", "")).decode("utf-8")
                params = store.unpack_secret(sec_raw)
                sec = base64.b32decode(params["secret_b32"] + "=" * (-len(params["secret_b32"]) % 8))
                self.cache[r["id"]] = {"issuer": iss, "label": lab, "secret": sec,
                                        **{k: params[k] for k in ("digits", "period", "algo")}}
            except ValueError:
                continue
        q = self.search.text().strip().lower()
        if q:
            ids = [i for i, d in self.cache.items()
                   if q in d["issuer"].lower() or q in d["label"].lower()]
        else:
            ids = list(self.cache.keys())
        # Limpia filas
        while self.vbox.count() > 1:
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for acc_id in ids:
            d = self.cache[acc_id]
            code = totp.generate(d["secret"], digits=d["digits"],
                                 period=d["period"], algo=d["algo"])
            remain = totp.seconds_remaining(period=d["period"])
            row = AccountRow(self, acc_id, d["issuer"], d["label"], code,
                             remain, d["period"], self.trash_mode)
            row.setProperty("acc", acc_id)
            self.vbox.insertWidget(self.vbox.count() - 1, row)
        a, b = store.count_accounts()
        self.lbl_count.setText(f"{b} en papelera" if self.trash_mode else f"{a} cuentas")
        if not keep_codes:
            anim.stagger([self.vbox.itemAt(i).widget() for i in range(self.vbox.count() - 1)
                          if self.vbox.itemAt(i).widget()])

    def _tick(self):
        if self.w.key is None or not self.isVisible():
            return
        for i in range(self.vbox.count() - 1):
            row = self.vbox.itemAt(i).widget()
            if not isinstance(row, AccountRow):
                continue
            d = self.cache.get(row.acc_id)
            if not d:
                continue
            try:
                code = totp.generate(d["secret"], digits=d["digits"],
                                     period=d["period"], algo=d["algo"])
                row.refresh(code, totp.seconds_remaining(period=d["period"]))
            except ValueError:
                continue

    # ---- acciones ----
    def copy_code(self, acc_id: str):
        d = self.cache.get(acc_id)
        if not d:
            return
        code = totp.generate(d["secret"], digits=d["digits"],
                             period=d["period"], algo=d["algo"])
        copy_and_clear(code)
        show_toast(self.w, f"Código copiado · se limpia en {settings.get_clipboard_sec()}s")
        # La semilla JAMAS va al clipboard persistente: solo el codigo de 6-8 digitos.

    def row_menu(self, acc_id: str, btn: QWidget):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu
        m = QMenu(self)
        if self.trash_mode:
            a_res = QAction("Restaurar", self)
            a_res.triggered.connect(lambda: self._restore(acc_id))
            a_del = QAction("Eliminar definitivo", self)
            a_del.triggered.connect(lambda: self._hard_delete(acc_id))
            m.addActions([a_res, a_del])
        else:
            a_ren = QAction("Renombrar", self)
            a_ren.triggered.connect(lambda: self._rename(acc_id))
            a_up = QAction("Subir", self)
            a_up.triggered.connect(lambda: self._move(acc_id, -1))
            a_dn = QAction("Bajar", self)
            a_dn.triggered.connect(lambda: self._move(acc_id, 1))
            a_del = QAction("Eliminar (papelera)", self)
            a_del.triggered.connect(lambda: self._soft_delete(acc_id))
            m.addActions([a_ren, a_up, a_dn, a_del])
        try:
            m.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        except Exception:
            pass

    def _toggle_trash(self):
        self.trash_mode = self.b_trash.isChecked()
        self.b_trash.setText("Volver" if self.trash_mode else "Papelera")
        self.reload()

    def _soft_delete(self, acc_id: str):
        store.delete_account(acc_id)
        show_toast(self.w, "Movido a la papelera (30 días)")
        self.reload(keep_codes=True)

    def _restore(self, acc_id: str):
        store.restore_account(acc_id)
        self.reload(keep_codes=True)

    def _hard_delete(self, acc_id: str):
        r = QMessageBox.question(self, "Eliminar", "Eliminación definitiva. ¿Continuar?")
        if r == QMessageBox.Yes:
            store.hard_delete_account(acc_id)
            self.reload(keep_codes=True)

    def _rename(self, acc_id: str):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout
        d = self.cache.get(acc_id)
        if not d:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Renombrar")
        lay = QFormLayout(dlg)
        e_iss, e_lab = QLineEdit(d["issuer"]), QLineEdit(d["label"])
        lay.addRow("Emisor", e_iss)
        lay.addRow("Etiqueta", e_lab)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        key = self.w.key
        assert key is not None
        store.rename_account(acc_id, vault.encrypt(key, e_iss.text().strip().encode()),
                             vault.encrypt(key, e_lab.text().strip().encode()))
        self.reload(keep_codes=True)

    def _move(self, acc_id: str, delta: int):
        rows = store.list_accounts_meta()
        ids = [r["id"] for r in rows]
        if acc_id not in ids:
            return
        i = ids.index(acc_id)
        j = max(0, min(len(ids) - 1, i + delta))
        ids.insert(j, ids.pop(i))
        store.reorder(ids)
        self.reload(keep_codes=True)

    def purge_old(self):
        n = store.purge_deleted(30)
        if n:
            show_toast(self.w, f"Papelera purgada: {n}")
            self.reload(keep_codes=True)
