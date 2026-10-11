"""Preferencias completas: sub-nav + 6 secciones funcionales con transiciones."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from app import auth, settings, store, vault
from app.version import APP_VERSION
from ui.styles import animations as anim
from ui.widgets.toasts import show_toast


class PrefsScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        self._host = None  # lo fija open_prefs_modal para poder cerrarse
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)
        # Sub-nav
        self.nav = QListWidget()
        self.nav.setObjectName("prefNav")
        self.nav.setFixedWidth(190)
        self.nav.addItems(["General", "Seguridad", "Clave maestra",
                           "Recuperación y copias", "Actualizaciones", "Peligro"])
        try:
            from ui.widgets.icons import icon as _ic
            for row, name in enumerate(["grid", "shield", "key", "download", "refresh", "alert"]):
                item = self.nav.item(row)
                if item is not None:
                    item.setIcon(_ic(name))
        except Exception:
            pass
        self.nav.setCurrentRow(0)
        lay.addWidget(self.nav)
        self.pages = QStackedWidget()
        lay.addWidget(self.pages, 1)
        self._sec_general = self._build_general()
        self._sec_seguridad = self._build_seguridad()
        self._sec_clave = self._build_clave()
        self._sec_copias = self._build_copias()
        self._sec_updates = self._build_updates()
        self._sec_peligro = self._build_peligro()
        for s in (self._sec_general, self._sec_seguridad, self._sec_clave,
                  self._sec_copias, self._sec_updates, self._sec_peligro):
            self.pages.addWidget(s)
        self.nav.currentRowChanged.connect(self._goto)
        self.refresh_stats()

    def _goto(self, i: int):
        self.pages.setCurrentIndex(i)
        anim.fade_in(self.pages.currentWidget(), 180)

    # ---------- envoltorio con scroll ----------
    @staticmethod
    def _wrap(inner: QWidget) -> QWidget:
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QScrollArea.NoFrame)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(6, 4, 12, 12)
        lay.setSpacing(10)
        lay.addWidget(inner)
        lay.addStretch(1)
        sc.setWidget(holder)
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(sc)
        return page

    @staticmethod
    def _card() -> tuple[QWidget, QVBoxLayout]:
        c = QWidget()
        c.setObjectName("card")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        return c, lay

    # ---------- General ----------
    def _build_general(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_h("General"))
        stats, sl = self._card()
        self.lbl_stats = QLabel("…")
        self.lbl_stats.setObjectName("muted")
        self.lbl_stats.setWordWrap(True)
        sl.addWidget(QLabel("Tu bóveda de un vistazo:"))
        sl.addWidget(self.lbl_stats)
        lay.addWidget(stats)
        blk, bl = self._card()
        bl.addWidget(_h("Bloqueo automático"))
        row = QHBoxLayout()
        self.c_lock = QComboBox()
        self.c_lock.addItems(["1", "3", "5", "10"])
        self.c_lock.setCurrentText(str(settings.get_autolock_min()))
        self.c_lock.currentTextChanged.connect(lambda t: settings.set_autolock_min(int(t)))
        row.addWidget(QLabel("Bloquear tras (min):"))
        row.addWidget(self.c_lock, 1)
        bl.addLayout(row)
        self.chk_min = QCheckBox("Bloquear al minimizar")
        self.chk_min.setChecked(settings.get_lock_on_minimize())
        self.chk_min.toggled.connect(settings.set_lock_on_minimize)
        bl.addWidget(self.chk_min)
        b_lock = QPushButton("Bloquear ahora")
        b_lock.setObjectName("ghost")
        b_lock.clicked.connect(lambda: self.w.lock())
        bl.addWidget(b_lock)
        lay.addWidget(blk)
        clip, cl = self._card()
        cl.addWidget(_h("Portapapeles"))
        row2 = QHBoxLayout()
        self.c_clip = QComboBox()
        self.c_clip.addItems(["10", "15", "30", "60"])
        self.c_clip.setCurrentText(str(settings.get_clipboard_sec()))
        self.c_clip.currentTextChanged.connect(lambda t: settings.set_clipboard_sec(int(t)))
        row2.addWidget(QLabel("Auto-limpieza (s):"))
        row2.addWidget(self.c_clip, 1)
        cl.addLayout(row2)
        cl.addWidget(_muted("Solo se copia el código de 6–8 dígitos; la semilla jamás sale de la bóveda."))
        lay.addWidget(clip)
        app_, al = self._card()
        al.addWidget(_h("Apariencia"))
        self.chk_motion = QCheckBox("Reducir animaciones")
        self.chk_motion.setChecked(settings.get_reduced_motion())
        self.chk_motion.toggled.connect(self._motion)
        al.addWidget(self.chk_motion)
        lay.addWidget(app_)
        return self._wrap(box)

    def refresh_stats(self):
        try:
            a, b = store.count_accounts()
            self.lbl_stats.setText(f"{a} cuentas activas · {b} en papelera")
            if getattr(self.w, "sidebar", None) is not None:
                self.w.sidebar.set_trash_count(b)
        except Exception:
            pass

    def _motion(self, v: bool):
        settings.set_reduced_motion(v)
        anim.set_reduced(v)

    # ---------- Seguridad ----------
    def _build_seguridad(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_h("Seguridad"))
        c, cl = self._card()
        cl.addWidget(_muted("KDF Argon2id (t=3, 64 MiB, p=4) · AES-256-GCM · backoff tras 5 intentos "
                            "(5s, 15s, 30s, 60s) · permisos 0600/0700 · cero red salvo chequeo de versión opt-in."))
        cl.addWidget(_muted(self._session_status()))
        b_verify = QPushButton("Verificar integridad")
        b_verify.setObjectName("ghost")
        b_verify.clicked.connect(self._verify)
        cl.addWidget(b_verify)
        lay.addWidget(c)
        return self._wrap(box)

    @staticmethod
    def _session_status() -> str:
        import sys
        if sys.platform == "win32":
            return "Bloqueo con Win+L / suspensión: activo (se bloquea al bloquear la sesión)."
        return "Bloqueo con Win+L: no disponible fuera de Windows (sigue activo el autobloqueo por tiempo)."

    def _verify(self):
        key = self.w.key
        if key is None:
            return
        try:
            for r in store.list_accounts_meta(include_deleted=True):
                for f in ("issuer_blob", "label_blob", "secret_blob"):
                    if r.get(f):
                        vault.decrypt(key, r[f])
            show_toast(self.w, "Integridad OK")
        except ValueError:
            QMessageBox.warning(self, "Integridad", "Hay registros corruptos o ilegibles.")

    # ---------- Clave maestra ----------
    def _build_clave(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_h("Clave maestra"))
        c, cl = self._card()
        cl.addWidget(_muted("Cambiar la clave re-cifra TODAS las cuentas en una transacción atómica. "
                            "El kit anterior queda invalidado: crea uno nuevo después."))
        self.e_cur = QLineEdit()
        self.e_cur.setEchoMode(QLineEdit.Password)
        self.e_cur.setPlaceholderText("Clave actual")
        self.e_new1 = QLineEdit()
        self.e_new1.setEchoMode(QLineEdit.Password)
        self.e_new1.setPlaceholderText("Nueva clave (12+, 3 de 4 clases)")
        self.e_new2 = QLineEdit()
        self.e_new2.setEchoMode(QLineEdit.Password)
        self.e_new2.setPlaceholderText("Repite la nueva")
        for e in (self.e_cur, self.e_new1, self.e_new2):
            cl.addWidget(e)
        b_ch = QPushButton("Cambiar clave y re-cifrar todo")
        b_ch.setObjectName("primary")
        b_ch.clicked.connect(self._change)
        cl.addWidget(b_ch)
        lay.addWidget(c)
        return self._wrap(box)

    def _change(self):
        if self.e_new1.text() != self.e_new2.text():
            QMessageBox.warning(self, "Aviso", "Las claves nuevas no coinciden.")
            return
        try:
            new_key = auth.change_master(self.w.key, self.e_cur.text(), self.e_new1.text())
        except ValueError as e:
            QMessageBox.warning(self, "Aviso", str(e))
            return
        self.w.key = new_key
        for e in (self.e_cur, self.e_new1, self.e_new2):
            e.clear()
        show_toast(self.w, "Clave cambiada. Crea un kit nuevo en Recuperación.")

    # ---------- Recuperación y copias ----------
    def _build_copias(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_h("Recuperación y copias"))
        k, kl = self._card()
        kl.addWidget(_muted("El kit offline es la única salida si olvidas la clave. Rotarlo invalida el anterior."))
        b_kit = QPushButton("Ver / rotar kit de recuperación")
        b_kit.setObjectName("ghost")
        b_kit.clicked.connect(self._kit)
        kl.addWidget(b_kit)
        lay.addWidget(k)
        c, cl = self._card()
        cl.addWidget(_muted("Copias 100% cifradas. Al importar, el archivo de origen se tritura."))
        last = settings.get_last_backup() or "sin copias aún"
        self.lbl_bak = QLabel(f"Última copia: {last}")
        self.lbl_bak.setObjectName("muted")
        self.lbl_bak.setWordWrap(True)
        cl.addWidget(self.lbl_bak)
        rb = QHBoxLayout()
        b_exp = QPushButton("Exportar copia")
        b_exp.setObjectName("ghost")
        b_exp.clicked.connect(self._export)
        b_imp = QPushButton("Importar + triturar origen")
        b_imp.setObjectName("ghost")
        b_imp.clicked.connect(self._import)
        rb.addWidget(b_exp, 1)
        rb.addWidget(b_imp, 1)
        cl.addLayout(rb)
        lay.addWidget(c)
        return self._wrap(box)

    def _close_host(self):
        try:
            if self._host is not None:
                self._host.accept()
        except (RuntimeError, Exception):
            pass

    def _kit(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        d = QDialog(self)
        d.setWindowTitle("Kit de recuperación")
        lay = QVBoxLayout(d)
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.Password)
        pw.setPlaceholderText("Clave actual")
        lay.addWidget(QLabel("Escribe tu clave actual para ver/rotar el kit:"))
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
        self._close_host()
        self.w.show_kit(code, first_time=True)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar copia cifrada",
                                               "authenticator-backup.json", "*.json")
        if not path:
            return
        data = store.export_encrypted()
        Path(path).write_text(json.dumps(data), encoding="utf-8")
        try:
            import os as _os
            _os.chmod(path, 0o600)
        except Exception:
            pass
        settings.set_last_backup(path)
        self.lbl_bak.setText(f"Última copia: {path}")
        show_toast(self.w, "Copia cifrada exportada")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar copia cifrada", "", "*.json")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            n, skip = store.import_encrypted(data, merge=True)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Aviso", f"No se pudo importar: {e}")
            return
        store.shred_file(path)
        show_toast(self.w, f"Importados {n}, omitidos {skip}. Origen triturado.")
        self.w.show_accounts()
        self.refresh_stats()

    # ---------- Actualizaciones ----------
    def _build_updates(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_h("Actualizaciones"))
        c, cl = self._card()
        cl.addWidget(QLabel(f"Versión instalada: {APP_VERSION}"))
        self.chk_upd = QCheckBox("Buscar actualizaciones al abrir")
        self.chk_upd.setChecked(settings.get_auto_update())
        self.chk_upd.setToolTip("Solo entonces la app usa red (api.github.com, HTTPS).")
        self.chk_upd.toggled.connect(settings.set_auto_update)
        cl.addWidget(self.chk_upd)
        skipped = settings.get_skipped_version()
        if skipped:
            cl.addWidget(_muted(f"Versión omitida: {skipped}"))
        row = QHBoxLayout()
        b_upd = QPushButton("Buscar ahora")
        b_upd.setObjectName("primary")
        b_upd.clicked.connect(self._check_update)
        b_reset = QPushButton("Restablecer avisos")
        b_reset.setObjectName("ghost")
        b_reset.setToolTip("Vuelve a avisar de versiones omitidas.")
        b_reset.clicked.connect(self._reset_skipped)
        row.addWidget(b_upd, 1)
        row.addWidget(b_reset, 1)
        cl.addLayout(row)
        lay.addWidget(c)
        return self._wrap(box)

    def _check_update(self):
        from ui.widgets.update_modal import check_now
        check_now(self.w, APP_VERSION)

    def _reset_skipped(self):
        settings.set_skipped_version("")
        show_toast(self.w, "Avisos restablecidos")

    # ---------- Peligro ----------
    def _build_peligro(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_h("Zona de peligro"))
        c, cl = self._card()
        cl.addWidget(_muted("Borra TODA la bóveda (cuentas + ajustes). Exige tu clave actual. "
                            "Sin kit ni copia, no hay vuelta atrás."))
        b_wipe = QPushButton("Borrar toda la bóveda…")
        b_wipe.setObjectName("danger")
        b_wipe.clicked.connect(self._wipe)
        cl.addWidget(b_wipe)
        lay.addWidget(c)
        return self._wrap(box)

    def _wipe(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        d = QDialog(self)
        d.setWindowTitle("Borrar todo")
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel("Escribe tu clave actual para borrar TODA la bóveda:"))
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.Password)
        lay.addWidget(pw)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        if d.exec() != QDialog.Accepted:
            return
        try:
            key = auth.login(pw.text())
        except ValueError:
            QMessageBox.warning(self, "Aviso", "La clave actual no es correcta.")
            return
        store.wipe_all()
        vault.wipe(key)
        show_toast(self.w, "Bóveda borrada")
        self._close_host()
        self.w.lock()


def _h(t: str) -> QLabel:
    l = QLabel(t)
    l.setStyleSheet("font-size: 16px; font-weight: 700;")
    return l


def open_prefs_modal(window) -> None:
    """Preferencias en modal centrado profesional (bloqueante, con X)."""
    from PySide6.QtCore import QRect, QTimer
    from ui.styles import animations as _anim
    from ui.widgets.icons import icon as _icon
    from ui.widgets.modal import ModalHost

    host = ModalHost(window)
    host.card.setMinimumSize(880, 620)
    host.card.setMaximumSize(960, 700)
    lay = QVBoxLayout(host.card)
    lay.setContentsMargins(20, 16, 20, 16)
    lay.setSpacing(10)
    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)
    title = QLabel("Preferencias")
    title.setStyleSheet("font-size: 20px; font-weight: 700;")
    head.addWidget(title, 1)
    b_x = QPushButton()
    b_x.setObjectName("iconBtn")
    b_x.setIcon(_icon("x"))
    b_x.setToolTip("Cerrar")
    b_x.setFixedSize(36, 36)
    b_x.clicked.connect(host.reject)
    head.addWidget(b_x)
    lay.addLayout(head)
    prefs = PrefsScreen(window)
    prefs._host = host
    prefs.refresh_stats()
    lay.addWidget(prefs, 1)
    # Geometria de pantalla completa (igual que open_animated) + exec bloqueante.
    try:
        top = window.mapToGlobal(window.rect().topLeft())
        host.setGeometry(QRect(top, window.size()))
    except Exception:
        pass
    QTimer.singleShot(60, lambda: _anim.fade_in(host.card, 200))
    try:
        host.exec()
    finally:
        try:
            sb = getattr(window, "sidebar", None)
            if sb is not None and getattr(window, "scr", None) is not None:
                sb.set_active("trash" if window.scr.trash_mode else "accounts")
        except (RuntimeError, Exception):
            pass
        host.deleteLater()


def _muted(t: str) -> QLabel:
    l = QLabel(t)
    l.setObjectName("muted")
    l.setWordWrap(True)
    return l
