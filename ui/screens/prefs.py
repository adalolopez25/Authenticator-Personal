"""Preferencias: modal con sub-nav + 6 secciones. Solo microcopy de accion."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout,
                               QWidget)

from app import auth, settings, store, vault
from app.version import APP_VERSION
from ui.styles import animations as anim
from ui.widgets.info import InfoBox
from ui.widgets.toasts import show_toast


def _section(ic: str, title: str) -> tuple[QWidget, QVBoxLayout]:
    """Tarjeta de seccion con header (icono + titulo)."""
    from ui.widgets.icons import icon as _icon
    card = QWidget()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(18, 14, 18, 16)
    lay.setSpacing(10)
    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)
    head.setSpacing(10)
    art = QLabel()
    art.setPixmap(_icon(ic).pixmap(22, 22))
    art.setFixedSize(24, 24)
    head.addWidget(art)
    t = QLabel(title)
    t.setStyleSheet("font-size: 16px; font-weight: 700;")
    head.addWidget(t, 1)
    lay.addLayout(head)
    return card, lay


class PrefsScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        self._host = None  # lo fija open_prefs_modal para poder cerrarse
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)
        self.nav = QListWidget()
        self.nav.setObjectName("prefNav")
        self.nav.setFixedWidth(196)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        for s in (self._build_general(), self._build_seguridad(), self._build_clave(),
                  self._build_copias(), self._build_updates(), self._build_peligro()):
            self.pages.addWidget(s)
        self.nav.currentRowChanged.connect(self._goto)
        self.refresh_stats()

    def _goto(self, i: int):
        self.pages.setCurrentIndex(i)
        anim.fade_in(self.pages.currentWidget(), 180)

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

    def _close_host(self):
        try:
            if self._host is not None:
                self._host.accept()
        except (RuntimeError, Exception):
            pass

    # ---------- General ----------
    def _build_general(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        stats = QHBoxLayout()
        stats.setContentsMargins(0, 0, 0, 0)
        stats.setSpacing(10)
        self.tile_a = self._stat_tile()
        self.tile_b = self._stat_tile()
        stats.addWidget(self.tile_a, 1)
        stats.addWidget(self.tile_b, 1)
        lay.addLayout(stats)
        c, cl = _section("clock", "Bloqueo automático")
        row = QHBoxLayout()
        row.addWidget(QLabel("Bloquear tras (min):"))
        self.c_lock = QComboBox()
        self.c_lock.addItems(["1", "3", "5", "10"])
        self.c_lock.setCurrentText(str(settings.get_autolock_min()))
        self.c_lock.setToolTip("Minutos de inactividad antes de bloquear")
        self.c_lock.currentTextChanged.connect(lambda t: settings.set_autolock_min(int(t)))
        row.addWidget(self.c_lock, 1)
        cl.addLayout(row)
        self.chk_min = QCheckBox("Bloquear al minimizar")
        self.chk_min.setChecked(settings.get_lock_on_minimize())
        self.chk_min.setToolTip("Bloquea también al minimizar la ventana")
        self.chk_min.toggled.connect(settings.set_lock_on_minimize)
        cl.addWidget(self.chk_min)
        b_lock = QPushButton("Bloquear ahora")
        b_lock.setObjectName("ghost")
        b_lock.setIcon(self._ic("lock"))
        b_lock.setToolTip("Bloquea la app inmediatamente")
        b_lock.clicked.connect(lambda: self.w.lock())
        cl.addWidget(b_lock)
        lay.addWidget(c)
        k, kl = _section("copy", "Portapapeles")
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Auto-limpieza (s):"))
        self.c_clip = QComboBox()
        self.c_clip.addItems(["10", "15", "30", "60"])
        self.c_clip.setCurrentText(str(settings.get_clipboard_sec()))
        self.c_clip.setToolTip("Segundos antes de borrar lo copiado")
        self.c_clip.currentTextChanged.connect(lambda t: settings.set_clipboard_sec(int(t)))
        row2.addWidget(self.c_clip, 1)
        kl.addLayout(row2)
        lay.addWidget(k)
        a, al = _section("sliders", "Apariencia")
        self.chk_motion = QCheckBox("Reducir animaciones")
        self.chk_motion.setChecked(settings.get_reduced_motion())
        self.chk_motion.setToolTip("Desactiva transiciones y efectos")
        self.chk_motion.toggled.connect(self._motion)
        al.addWidget(self.chk_motion)
        lay.addWidget(a)
        return self._wrap(box)

    @staticmethod
    def _ic(name: str):
        from ui.widgets.icons import icon as _icon
        return _icon(name)

    @staticmethod
    def _stat_tile() -> QWidget:
        t = QWidget()
        t.setObjectName("statTile")
        lay = QVBoxLayout(t)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        num = QLabel("–")
        num.setObjectName("statNum")
        lay.addWidget(num)
        lab = QLabel("")
        lab.setObjectName("muted")
        lay.addWidget(lab)
        t.setProperty("num", num)
        t.setProperty("lab", lab)
        return t

    def refresh_stats(self):
        try:
            a, b = store.count_accounts()
            for tile, n, lab in ((self.tile_a, a, "Cuentas"), (self.tile_b, b, "En papelera")):
                tile.property("num").setText(str(n))
                tile.property("lab").setText(lab)
            if getattr(self.w, "sidebar", None) is not None:
                self.w.sidebar.set_trash_count(b)
        except (RuntimeError, Exception):
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
        c, cl = _section("shield", "Integridad de la bóveda")
        self.lbl_integrity = QLabel("Sin verificar en esta sesión")
        self.lbl_integrity.setObjectName("muted")
        cl.addWidget(self.lbl_integrity)
        b_verify = QPushButton("Verificar integridad")
        b_verify.setObjectName("ghost")
        b_verify.setIcon(self._ic("check"))
        b_verify.setToolTip("Comprueba que todos los registros descifran bien")
        b_verify.clicked.connect(self._verify)
        cl.addWidget(b_verify)
        lay.addWidget(c)
        import sys as _sys
        if _sys.platform == "win32":
            lay.addWidget(InfoBox("El bloqueo con Win+L está activo en este equipo.", tone="ok"))
        else:
            lay.addWidget(InfoBox("Sigue activo el bloqueo por inactividad.", tone="info"))
        return self._wrap(box)

    def _verify(self):
        key = self.w.key
        if key is None:
            return
        try:
            for r in store.list_accounts_meta(include_deleted=True):
                for f in ("issuer_blob", "label_blob", "secret_blob"):
                    if r.get(f):
                        vault.decrypt(key, r[f])
            self.lbl_integrity.setText("Verificada correctamente")
            show_toast(self.w, "Integridad OK")
        except ValueError:
            self.lbl_integrity.setText("Fallo: hay registros ilegibles")
            QMessageBox.warning(self, "Integridad", "Hay registros corruptos o ilegibles.")

    # ---------- Clave maestra ----------
    def _build_clave(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        c, cl = _section("key", "Cambiar clave maestra")
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
        b_ch.setIcon(self._ic("check"))
        b_ch.setToolTip("Re-cifra todas las cuentas con la clave nueva")
        b_ch.clicked.connect(self._change)
        cl.addWidget(b_ch)
        lay.addWidget(c)
        lay.addWidget(InfoBox("El kit anterior deja de funcionar: crea uno nuevo después.", tone="warn"))
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
        show_toast(self.w, "Clave cambiada. Crea un kit nuevo.")

    # ---------- Recuperación y copias ----------
    def _build_copias(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        k, kl = _section("download", "Kit de recuperación")
        b_kit = QPushButton("Ver / rotar kit")
        b_kit.setObjectName("ghost")
        b_kit.setIcon(self._ic("key"))
        b_kit.setToolTip("Muestra un kit nuevo e invalida el anterior")
        b_kit.clicked.connect(self._kit)
        kl.addWidget(b_kit)
        lay.addWidget(k)
        c, cl = _section("copy", "Copias de seguridad")
        last = settings.get_last_backup() or "Sin copias aún"
        self.lbl_bak = QLabel(last)
        self.lbl_bak.setObjectName("muted")
        self.lbl_bak.setWordWrap(True)
        cl.addWidget(self.lbl_bak)
        rb = QHBoxLayout()
        b_exp = QPushButton("Exportar")
        b_exp.setObjectName("ghost")
        b_exp.setIcon(self._ic("upload"))
        b_exp.setToolTip("Guarda una copia cifrada en un archivo")
        b_exp.clicked.connect(self._export)
        b_imp = QPushButton("Importar")
        b_imp.setObjectName("ghost")
        b_imp.setIcon(self._ic("download"))
        b_imp.setToolTip("Restaura una copia y tritura el archivo de origen")
        b_imp.clicked.connect(self._import)
        rb.addWidget(b_exp, 1)
        rb.addWidget(b_imp, 1)
        cl.addLayout(rb)
        lay.addWidget(c)
        return self._wrap(box)

    def _kit(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        d = QDialog(self)
        d.setWindowTitle("Kit de recuperación")
        lay = QVBoxLayout(d)
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.Password)
        pw.setPlaceholderText("Clave actual")
        lay.addWidget(QLabel("Clave actual:"))
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
        self.lbl_bak.setText(path)
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
        c, cl = _section("refresh", "Versión y actualizaciones")
        ver = QHBoxLayout()
        ver.addWidget(QLabel(f"Instalada: {APP_VERSION}"))
        ver.addStretch(1)
        cl.addLayout(ver)
        self.chk_upd = QCheckBox("Buscar actualizaciones al abrir")
        self.chk_upd.setChecked(settings.get_auto_update())
        self.chk_upd.setToolTip("Solo entonces la app usa red (api.github.com, HTTPS)")
        self.chk_upd.toggled.connect(settings.set_auto_update)
        cl.addWidget(self.chk_upd)
        row = QHBoxLayout()
        b_upd = QPushButton("Buscar ahora")
        b_upd.setObjectName("primary")
        b_upd.setIcon(self._ic("refresh"))
        b_upd.setToolTip("Comprueba si hay una versión nueva")
        b_upd.clicked.connect(self._check_update)
        b_reset = QPushButton("Restablecer avisos")
        b_reset.setObjectName("ghost")
        b_reset.setToolTip("Vuelve a avisar de versiones omitidas")
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
        c, cl = _section("alert", "Borrar bóveda")
        cl.addWidget(InfoBox("Borra cuentas y ajustes. Pide tu clave actual y no se puede deshacer.",
                             tone="danger"))
        b_wipe = QPushButton("Borrar todo…")
        b_wipe.setObjectName("danger")
        b_wipe.setIcon(self._ic("trash"))
        b_wipe.setToolTip("Borra definitivamente toda la bóveda")
        b_wipe.clicked.connect(self._wipe)
        cl.addWidget(b_wipe)
        lay.addWidget(c)
        return self._wrap(box)

    def _wipe(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        d = QDialog(self)
        d.setWindowTitle("Borrar todo")
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel("Clave actual:"))
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
    b_x.setToolTip("Cerrar preferencias")
    b_x.setFixedSize(36, 36)
    b_x.clicked.connect(host.reject)
    head.addWidget(b_x)
    lay.addLayout(head)
    prefs = PrefsScreen(window)
    prefs._host = host
    prefs.refresh_stats()
    lay.addWidget(prefs, 1)
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
