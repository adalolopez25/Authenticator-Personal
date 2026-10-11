"""Vista de cuentas: mosaicos grandes por emisor; el codigo vive en su modal."""
from __future__ import annotations

import base64

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from app import settings, store, vault
from app.utils import clipboard_history_on, copy_and_clear
from ui.styles import animations as anim
from ui.widgets.icons import icon
from ui.widgets.issuer import art_label
from ui.widgets.toasts import show_toast


class AccountTile(QWidget):
    """Mosaico grande: icono de plataforma o monograma + nombres. Clic = modal."""

    def __init__(self, parent_list, acc_id: str, issuer: str, label: str):
        super().__init__()
        self.L = parent_list
        self.acc_id = acc_id
        self.setObjectName("tile")
        # OBLIGATORIO en widgets custom con fondo QSS: sin esto el fondo
        # NO se pinta en la ventana (solo en grab propio). Ver AGENTS §21.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(220, 170)
        self.setToolTip(f"Ver código de {issuer or label or 'la cuenta'}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(16)
        lay.addWidget(art_label(issuer, label, 88))
        txt = QVBoxLayout()
        txt.setContentsMargins(0, 0, 0, 0)
        txt.setSpacing(4)
        name = QLabel(issuer or label or "Cuenta")
        name.setObjectName("tileName")
        name.setWordWrap(True)
        txt.addWidget(name)
        sub = QLabel(label if issuer else "")
        sub.setObjectName("tileSub")
        sub.setWordWrap(True)
        txt.addWidget(sub)
        txt.addStretch(1)
        lay.addLayout(txt, 1)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        from ui.widgets.account_modal import open_account_modal
        try:
            open_account_modal(self.L.w, self.acc_id)
        except (RuntimeError, AttributeError):
            pass
        super().mousePressEvent(event)


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
        s = QLabel("Se eliminan solas con el tiempo." if trash
                   else "Añade tu primera cuenta para empezar.")
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
        self._cols = 0
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
        self.grid = QGridLayout(self.inner)
        self.grid.setContentsMargins(0, 2, 0, 2)
        self.grid.setSpacing(10)
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll, 1)
        # Footer: solo papelera (vaciar)
        self.b_empty = QPushButton("Vaciar papelera")
        self.b_empty.setObjectName("danger")
        self.b_empty.setIcon(icon("trash"))
        self.b_empty.setToolTip("Elimina definitivamente todo lo de la papelera")
        self.b_empty.clicked.connect(self._empty_trash)
        self.b_empty.setVisible(False)
        lay.addWidget(self.b_empty, 0, Qt.AlignRight)

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
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cols = max(1, self._cols_for_width())
        self._cols = cols
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)
        if not ids:
            empty = EmptyState(trash=self.trash_mode, on_add=lambda: self.w.show_add())
            self.grid.addWidget(empty, 0, 0, 1, cols)
        for n, acc_id in enumerate(ids):
            d = self.cache[acc_id]
            tile = AccountTile(self, acc_id, d["issuer"], d["label"])
            tile.setProperty("acc", acc_id)
            self.grid.addWidget(tile, n // cols, n % cols)
        self.grid.setRowStretch((len(ids) + cols - 1) // cols + 1, 1)
        a, b = store.count_accounts()
        self.lbl_count.setText(f"{b} en papelera" if self.trash_mode else f"{a} cuentas")
        self.b_empty.setVisible(self.trash_mode and b > 0)
        try:
            self.counts_changed.emit(a, b)
        except RuntimeError:
            pass
        if not keep_codes:
            anim.stagger([w for w in self._iter_tiles()])

    def _iter_tiles(self):
        for i in range(self.grid.count()):
            try:
                w = self.grid.itemAt(i).widget()
            except RuntimeError:
                continue
            if isinstance(w, AccountTile):
                yield w

    def set_trash_mode(self, trash: bool):
        """Cambia Cuentas <-> Papelera (lo ordena el sidebar)."""
        self.trash_mode = trash
        self.lbl_title.setText("Papelera" if trash else "Cuentas")
        self.search.clear()
        self.b_add_top.setVisible(not trash)
        self.reload()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        try:
            if self._cols_for_width() != self._cols and self.w.key is not None:
                self.reload(keep_codes=True)
        except RuntimeError:
            pass

    def _cols_for_width(self) -> int:
        """2 mosaicos grandes por fila en ancho (ocupan todo), 1 en estrecho."""
        try:
            return 2 if self.width() >= 600 else 1
        except RuntimeError:
            return 1

    def _empty_trash(self):
        rows = store.list_accounts_meta(deleted_only=True)
        if not rows:
            return
        r = QMessageBox.question(self, "Vaciar papelera",
                                 f"Elimina definitivamente {len(rows)} elemento(s). ¿Continuar?")
        if r != QMessageBox.Yes:
            return
        for it in rows:
            store.hard_delete_account(it["id"])
        show_toast(self.w, "Papelera vaciada")
        self.reload(keep_codes=True)

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

    def _soft_delete(self, acc_id: str):
        store.delete_account(acc_id)
        show_toast(self.w, "Movida a la papelera")
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
