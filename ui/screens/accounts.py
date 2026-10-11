"""Vista de cuentas: header con acciones, filas con avatar + copiar, estado vacio."""
from __future__ import annotations

import base64

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from app import settings, store, totp, vault
from app.utils import clipboard_history_on, copy_and_clear
from ui.styles import animations as anim
from ui.widgets.icons import icon
from ui.widgets.toasts import show_toast


def _initials(issuer: str, label: str) -> str:
    base = (issuer or label or "?").strip()
    parts = [p for p in base.replace("@", " ").replace(".", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


class AccountRow(QWidget):
    def __init__(self, parent_list, acc_id: str, issuer: str, label: str,
                 code: str, remain: int, period: int, trash_mode: bool = False):
        super().__init__()
        self.L = parent_list
        self.acc_id = acc_id
        self.setObjectName("row")
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        # Avatar 2 letras
        av = QLabel(_initials(issuer, label))
        av.setObjectName("avatar")
        av.setFixedSize(46, 46)
        av.setAlignment(Qt.AlignCenter)
        lay.addWidget(av)
        # Centro: nombre + codigo + countdown
        mid = QVBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(4)
        name = QLabel(f"{issuer} · {label}" if issuer and label else (issuer or label or "Cuenta"))
        name.setObjectName("issuer")
        mid.addWidget(name)
        self.lbl_code = QLabel(_fmt(code))
        self.lbl_code.setObjectName("code")
        mid.addWidget(self.lbl_code)
        self.bar = QProgressBar()
        self.bar.setObjectName("count")
        self.bar.setRange(0, max(1, period))
        self.bar.setValue(max(0, remain))
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        mid.addWidget(self.bar)
        lay.addLayout(mid, 1)
        # Acciones: copiar + menu
        side = QVBoxLayout()
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(2)
        self.b_menu = QPushButton("⋮")
        self.b_menu.setObjectName("toolBtn")
        self.b_menu.setFixedWidth(30)
        self.b_menu.clicked.connect(lambda: self.L.row_menu(self.acc_id, self.b_menu))
        side.addWidget(self.b_menu, 0, Qt.AlignRight)
        side.addStretch(1)
        self.b_copy = QPushButton()
        self.b_copy.setObjectName("iconBtn")
        self.b_copy.setIcon(icon("copy"))
        self.b_copy.setToolTip("Copiar código")
        self.b_copy.setFixedSize(34, 34)
        self.b_copy.clicked.connect(lambda: self.L.copy_code(self.acc_id))
        side.addWidget(self.b_copy, 0, Qt.AlignRight)
        lay.addLayout(side)
        self._set_urgent(remain)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        # Clic en la fila (no en botones) = copiar.
        child = self.childAt(event.pos())
        if isinstance(child, QPushButton) or (child and isinstance(child.parent(), QPushButton)):
            super().mousePressEvent(event)
            return
        self.L.copy_code(self.acc_id)
        super().mousePressEvent(event)

    def _set_urgent(self, remain: int) -> None:
        """Barra roja en los ultimos 5s (repolish por propiedad dinamica)."""
        urgent = remain <= 5
        if self.bar.property("urgent") != urgent:
            self.bar.setProperty("urgent", urgent)
            try:
                self.bar.style().unpolish(self.bar)
                self.bar.style().polish(self.bar)
            except RuntimeError:
                pass

    def refresh(self, code: str, remain: int):
        try:
            self.lbl_code.setText(_fmt(code))
            self.bar.setValue(max(0, remain))
            self._set_urgent(remain)
        except RuntimeError:
            pass  # fila borrada entre ticks: el proximo reload la limpia


def _fmt(code: str) -> str:
    return f"{code[:len(code) // 2]} {code[len(code) // 2:]}" if len(code) > 4 else code


class EmptyState(QWidget):
    """Estado vacio profesional con icono + CTA."""

    def __init__(self, trash: bool = False, on_add=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 48, 20, 48)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignCenter)
        art = QLabel("◈" if not trash else "○")
        art.setObjectName("emptyArt")
        art.setAlignment(Qt.AlignCenter)
        lay.addWidget(art)
        t = QLabel("Papelera vacía" if trash else "Sin cuentas todavía")
        t.setStyleSheet("font-size: 17px; font-weight: 700;")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)
        s = QLabel("Los elementos eliminados esperan aquí 30 días." if trash
                   else "Añade tu primera cuenta con el secreto o la URI del proveedor.")
        s.setObjectName("muted")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        lay.addWidget(s)
        if not trash and on_add is not None:
            b = QPushButton("Añadir mi primera cuenta")
            b.setObjectName("primary")
            b.setIcon(icon("plus"))
            b.clicked.connect(on_add)
            lay.addWidget(b, 0, Qt.AlignCenter)


class AccountsScreen(QWidget):
    counts_changed = Signal(int, int)  # (activas, papelera) para el badge del sidebar

    def __init__(self, window):
        super().__init__()
        self.w = window
        self.trash_mode = False
        self.cache: dict[str, dict] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)
        # Header: titulo + subtitulo + acciones
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        self.lbl_title = QLabel("Cuentas")
        self.lbl_title.setStyleSheet("font-size: 22px; font-weight: 700;")
        titles.addWidget(self.lbl_title)
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("muted")
        titles.addWidget(self.lbl_count)
        head.addLayout(titles, 1)
        self.b_refresh = QPushButton()
        self.b_refresh.setObjectName("iconBtn")
        self.b_refresh.setIcon(icon("refresh"))
        self.b_refresh.setToolTip("Recargar")
        self.b_refresh.setFixedSize(38, 38)
        self.b_refresh.clicked.connect(lambda: self.reload())
        head.addWidget(self.b_refresh)
        self.b_add_top = QPushButton("Añadir")
        self.b_add_top.setObjectName("primary")
        self.b_add_top.setIcon(icon("plus"))
        self.b_add_top.clicked.connect(lambda: self.w.show_add())
        head.addWidget(self.b_add_top)
        lay.addLayout(head)
        # Buscador
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Buscar cuenta…")
        self.search.addAction(icon("search"), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(lambda: self.reload(keep_codes=True))
        lay.addWidget(self.search)
        # Lista scrolleable
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.inner = QWidget()
        self.vbox = QVBoxLayout(self.inner)
        self.vbox.setContentsMargins(0, 2, 0, 2)
        self.vbox.setSpacing(10)
        self.vbox.addStretch(1)
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll, 1)
        # Footer
        self.lbl_foot = QLabel("")
        self.lbl_foot.setObjectName("muted")
        self.lbl_foot.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_foot)
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
        # Limpia filas (y posible estado vacio anterior)
        while self.vbox.count() > 1:
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not ids:
            empty = EmptyState(trash=self.trash_mode, on_add=lambda: self.w.show_add())
            self.vbox.insertWidget(self.vbox.count() - 1, empty)
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
        self.lbl_count.setText(f"{b} en papelera · purga a los 30 días" if self.trash_mode
                               else f"{a} cuentas protegidas con AES-256-GCM")
        self.lbl_foot.setText("Clic en una fila o en Copiar para copiar · se auto-limpia" if ids else "")
        try:
            self.counts_changed.emit(a, b)
        except RuntimeError:
            pass
        if not keep_codes:
            anim.stagger([self.vbox.itemAt(i).widget() for i in range(self.vbox.count() - 1)
                          if self.vbox.itemAt(i).widget()])

    def set_trash_mode(self, trash: bool):
        """Cambia Cuentas <-> Papelera (lo ordena el sidebar)."""
        self.trash_mode = trash
        self.lbl_title.setText("Papelera" if trash else "Cuentas")
        self.search.clear()
        self.b_add_top.setVisible(not trash)
        self.reload()

    def _tick(self):
        if self.w.key is None or not self.isVisible():
            return
        for i in range(self.vbox.count() - 1):
            try:
                row = self.vbox.itemAt(i).widget()
            except RuntimeError:
                continue
            if not isinstance(row, AccountRow):
                continue
            d = self.cache.get(row.acc_id)
            if not d:
                continue
            try:
                code = totp.generate(d["secret"], digits=d["digits"],
                                     period=d["period"], algo=d["algo"])
                row.refresh(code, totp.seconds_remaining(period=d["period"]))
            except (ValueError, RuntimeError):
                continue

    # ---- acciones ----
    def copy_code(self, acc_id: str):
        d = self.cache.get(acc_id)
        if not d:
            return
        code = totp.generate(d["secret"], digits=d["digits"],
                             period=d["period"], algo=d["algo"])
        copy_and_clear(code)
        msg = f"Código copiado · se limpia en {settings.get_clipboard_sec()}s"
        if clipboard_history_on():
            msg += " · aviso: Win+V conserva historial fuera de la app"
        show_toast(self.w, msg)
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
