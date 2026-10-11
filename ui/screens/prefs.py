"""Preferencias minimas (dialogo compacto, no ventana lateral)."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
                               QWidget)

from app import auth, settings, store, vault
from app.version import APP_VERSION
from ui.widgets.toasts import show_toast


class PrefsScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)
        lay.addWidget(_h("Preferencias"))
        # Autolock
        lay.addWidget(_h("Bloqueo automático"))
        row = QHBoxLayout()
        self.c_lock = QComboBox()
        self.c_lock.addItems(["1", "3", "5", "10"])
        self.c_lock.setCurrentText(str(settings.get_autolock_min()))
        self.c_lock.currentTextChanged.connect(lambda t: settings.set_autolock_min(int(t)))
        row.addWidget(QLabel("Bloquear tras (min):"))
        row.addWidget(self.c_lock, 1)
        lay.addLayout(row)
        self.chk_min = QCheckBox("Bloquear al minimizar")
        self.chk_min.setChecked(settings.get_lock_on_minimize())
        self.chk_min.toggled.connect(settings.set_lock_on_minimize)
        lay.addWidget(self.chk_min)
        b_lock = QPushButton("Bloquear ahora")
        b_lock.setObjectName("ghost")
        b_lock.clicked.connect(lambda: self.w.lock())
        lay.addWidget(b_lock)
        # Clipboard
        lay.addWidget(_h("Portapapeles"))
        row2 = QHBoxLayout()
        self.c_clip = QComboBox()
        self.c_clip.addItems(["10", "15", "30", "60"])
        self.c_clip.setCurrentText(str(settings.get_clipboard_sec()))
        self.c_clip.currentTextChanged.connect(lambda t: settings.set_clipboard_sec(int(t)))
        row2.addWidget(QLabel("Auto-limpieza (s):"))
        row2.addWidget(self.c_clip, 1)
        lay.addLayout(row2)
        # Animaciones
        self.chk_motion = QCheckBox("Reducir animaciones")
        self.chk_motion.setChecked(settings.get_reduced_motion())
        self.chk_motion.toggled.connect(self._motion)
        lay.addWidget(self.chk_motion)
        # Seguridad (solo lectura + verificar + cambio master + kit)
        lay.addWidget(_h("Seguridad"))
        lay.addWidget(_muted("KDF Argon2id (t=3, 64 MiB, p=4) · AES-256-GCM · backoff 5 intentos."))
        b_verify = QPushButton("Verificar integridad")
        b_verify.setObjectName("ghost")
        b_verify.clicked.connect(self._verify)
        lay.addWidget(b_verify)
        lay.addWidget(_muted("Cambiar clave maestra (re-cifra todo):"))
        self.e_cur = QLineEdit()
        self.e_cur.setEchoMode(QLineEdit.Password)
        self.e_cur.setPlaceholderText("Clave actual")
        self.e_new1 = QLineEdit()
        self.e_new1.setEchoMode(QLineEdit.Password)
        self.e_new1.setPlaceholderText("Nueva clave")
        self.e_new2 = QLineEdit()
        self.e_new2.setEchoMode(QLineEdit.Password)
        self.e_new2.setPlaceholderText("Repite la nueva")
        for e in (self.e_cur, self.e_new1, self.e_new2):
            lay.addWidget(e)
        b_ch = QPushButton("Cambiar clave")
        b_ch.setObjectName("primary")
        b_ch.clicked.connect(self._change)
        lay.addWidget(b_ch)
        b_kit = QPushButton("Ver / rotar kit de recuperación")
        b_kit.setObjectName("ghost")
        b_kit.clicked.connect(self._kit)
        lay.addWidget(b_kit)
        # Copias
        lay.addWidget(_h("Copias cifradas"))
        last = settings.get_last_backup() or "sin copias aún"
        self.lbl_bak = QLabel(f"Última copia: {last}")
        self.lbl_bak.setObjectName("muted")
        lay.addWidget(self.lbl_bak)
        rb = QHBoxLayout()
        b_exp = QPushButton("Exportar")
        b_exp.setObjectName("ghost")
        b_exp.clicked.connect(self._export)
        b_imp = QPushButton("Importar + triturar origen")
        b_imp.setObjectName("ghost")
        b_imp.clicked.connect(self._import)
        rb.addWidget(b_exp, 1)
        rb.addWidget(b_imp, 1)
        lay.addLayout(rb)
        # Acerca de + actualizaciones
        lay.addWidget(_h("Acerca de"))
        lay.addWidget(_muted(f"Authenticator {APP_VERSION} · offline · sin cuentas · sin nube.\n"
                             "Reloj sincronizado (NTP) requerido; TOTP no protege contra phishing."))
        lay.addWidget(_h("Actualizaciones"))
        self.chk_upd = QCheckBox("Buscar actualizaciones al abrir")
        self.chk_upd.setChecked(settings.get_auto_update())
        self.chk_upd.setToolTip("Solo entonces la app usa red (api.github.com, HTTPS).")
        self.chk_upd.toggled.connect(settings.set_auto_update)
        lay.addWidget(self.chk_upd)
        b_upd = QPushButton("Buscar actualizaciones ahora")
        b_upd.setObjectName("ghost")
        b_upd.clicked.connect(self._check_update)
        lay.addWidget(b_upd)
        b_back = QPushButton("Volver")
        b_back.setObjectName("ghost")
        b_back.clicked.connect(lambda: self.w.show_accounts())
        lay.addWidget(b_back)
        lay.addStretch(1)

    def _motion(self, v: bool):
        from ui.styles import animations as anim
        settings.set_reduced_motion(v)
        anim.set_reduced(v)

    def _check_update(self):
        from ui.widgets.update_modal import check_now
        check_now(self.w, APP_VERSION)

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

    def _kit(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        d = QDialog(self)
        d.setWindowTitle("Kit de recuperación")
        lay = QVBoxLayout(d)
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.Password)
        pw.setPlaceholderText("Clave actual")
        lay.addWidget(QLabel("Escribe tu clave actual para ver/rotar el kit:"))
        lay.addWidget(pw)
        from PySide6.QtWidgets import QDialogButtonBox
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
        store.shred_file(path)  # triturar origen al importar
        show_toast(self.w, f"Importados {n}, omitidos {skip}. Origen triturado.")
        self.w.show_accounts()


def _h(t: str) -> QLabel:
    l = QLabel(t)
    l.setStyleSheet("font-size: 15px; font-weight: 700;")
    return l


def _muted(t: str) -> QLabel:
    l = QLabel(t)
    l.setObjectName("muted")
    l.setWordWrap(True)
    return l
