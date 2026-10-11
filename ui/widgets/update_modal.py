"""Modal centrado de actualizacion: version nueva -> descargar + instalar en la app.

Flujo: muestra version actual -> disponible + notas -> "Actualizar ahora" descarga
el Setup oficial del release (con progreso) y lo lanza, cerrando la app para que
el instalador pueda reemplazar los archivos. "Omitir esta version" la silencia.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app import settings, update
from ui.styles import animations as anim
from ui.widgets.modal import ModalHost
from ui.widgets.toasts import show_toast


class _CheckThread(QThread):
    done = Signal(dict)
    failed = Signal()

    def run(self):  # noqa: N802
        try:
            self.done.emit(update.fetch_latest())
        except update.UpdateError:
            self.failed.emit()


class _DownloadThread(QThread):
    progress = Signal(int, int)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, dest: str):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):  # noqa: N802
        try:
            update.download(self.url, self.dest, self.progress.emit)
            self.done.emit(self.dest)
        except update.UpdateError as e:
            self.failed.emit(str(e))


class UpdateCard(QWidget):
    """Tarjeta interna del modal (vive dentro de un ModalHost)."""

    def __init__(self, host: ModalHost, window, info: dict, current: str):
        super().__init__()
        self.host = host
        self.w = window
        self.info = info
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)
        title = QLabel(f"Nueva versión disponible: {info['version']}")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        title.setWordWrap(True)
        lay.addWidget(title)
        sub = QLabel(f"Tienes la {current}. Se recomienda actualizar: incluye mejoras y correcciones.")
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        if info.get("notes"):
            notes = QLabel(info["notes"])
            notes.setObjectName("muted")
            notes.setWordWrap(True)
            notes.setMaximumHeight(140)
            lay.addWidget(notes)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setVisible(False)
        lay.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.b_go = QPushButton("Actualizar ahora")
        self.b_go.setObjectName("primary")
        self.b_go.clicked.connect(self._start)
        lay.addWidget(self.b_go)
        row2 = QVBoxLayout()
        self.b_later = QPushButton("Más tarde")
        self.b_later.setObjectName("ghost")
        self.b_later.clicked.connect(host.reject)
        self.b_skip = QPushButton(f"Omitir la {info['version']}")
        self.b_skip.setObjectName("toolBtn")
        self.b_skip.clicked.connect(self._skip)
        row2.addWidget(self.b_later)
        row2.addWidget(self.b_skip)
        lay.addLayout(row2)
        anim.fade_in(self, 200)

    def _start(self):
        self.b_go.setEnabled(False)
        self.b_later.setEnabled(False)
        self.bar.setVisible(True)
        self.status.setText("Descargando instalador oficial…")
        dest = str(Path(tempfile.mkdtemp(prefix="auth-upd-")) / update.SETUP_ASSET)
        self.th = _DownloadThread(self.info["setup_url"], dest)
        self.th.progress.connect(lambda d, t: self.bar.setValue(int(d * 100 / max(1, t))))
        self.th.done.connect(self._launch)
        self.th.failed.connect(self._fail)
        self.th.start()

    def _fail(self, msg: str):
        self.status.setText(f"No se pudo descargar: {msg}")
        self.b_go.setEnabled(True)
        self.b_later.setEnabled(True)

    def _launch(self, path: str):
        from PySide6.QtWidgets import QApplication
        try:
            update.launch_installer(path)
        except update.UpdateError as e:
            self._fail(str(e))
            return
        self.host.accept()
        show_toast(self.w, "Instalador lanzado: completa la actualización y reabre la app.")
        QApplication.instance().quit()

    def _skip(self):
        try:
            settings.set_skipped_version(self.info["version"])
        except Exception:
            pass
        self.host.reject()


def maybe_show_update(window, current: str) -> None:
    """Chequeo en hilo (no bloquea). Modal centrado solo si hay version mayor no omitida."""
    try:
        if not settings.get_auto_update():
            return
        skipped = settings.get_skipped_version()
    except Exception:
        return

    def _on(info: dict):
        try:
            if not update.is_newer(info["version"], current):
                return
            if skipped and info["version"] == skipped:
                return
            host = ModalHost(window)
            card = UpdateCard(host, window, info, current)
            host.card.setLayout(QVBoxLayout())
            host.card.layout().setContentsMargins(16, 16, 16, 16)
            host.card.layout().addWidget(card)
            host.open_animated()
        except Exception:
            pass

    th = _CheckThread(window)
    th.done.connect(_on)
    th.failed.connect(lambda: None)
    window._update_thread = th  # retiene referencia viva
    th.start()


def check_now(window, current: str) -> None:
    """Chequeo manual desde Preferencias (con aviso del resultado)."""
    try:
        info = update.fetch_latest()
    except update.UpdateError:
        QMessageBox.information(window, "Actualizaciones",
                                "No se pudo comprobar (sin conexión o tiempo agotado).")
        return
    if update.is_newer(info["version"], current):
        host = ModalHost(window)
        card = UpdateCard(host, window, info, current)
        host.card.setLayout(QVBoxLayout())
        host.card.layout().setContentsMargins(16, 16, 16, 16)
        host.card.layout().addWidget(card)
        host.open_animated()
    else:
        QMessageBox.information(window, "Actualizaciones",
                                f"Ya tienes la última versión ({current}).")
