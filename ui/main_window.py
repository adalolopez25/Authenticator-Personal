"""MainWindow escritorio: sidebar + contenido a pantalla amplia. Auth centrado.

Windows: ventana grande (1280x800) con sidebar colapsable a la izquierda y
paginas (Cuentas / Añadir / Papelera / Preferencias) con transicion fade.
Auth (welcome/unlock/kit): columna centrada sin sidebar.
El futuro build Android reutiliza las pantallas en columna unica sin sidebar.
"""
from __future__ import annotations

import time

from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QStackedWidget,
                               QVBoxLayout, QWidget)

from app import settings, store, vault
from ui.styles import animations as anim

AUTH_SIZE = (520, 780)
APP_SIZE = (1280, 800)
APP_MIN = (1024, 680)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.key: bytearray | None = None
        self._last_active = time.time()
        self.sidebar = None
        self.scr = None
        self._add = None
        self._prefs = None
        self.setWindowTitle("Authenticator")
        self.resize(*AUTH_SIZE)
        self.setMinimumSize(380, 600)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        self.root_lay = QVBoxLayout(root)
        self.root_lay.setContentsMargins(0, 0, 0, 0)
        self.root_lay.setSpacing(0)
        # Autolock por inactividad
        from PySide6.QtCore import QTimer
        self._idle = QTimer(self)
        self._idle.timeout.connect(self._check_idle)
        self._idle.start(10_000)
        anim.set_reduced(settings.get_reduced_motion())
        try:
            from ui.widgets.winframe import apply_dark_titlebar, watch_session_lock
            apply_dark_titlebar(self)
            watch_session_lock(self, self.lock)
        except Exception:
            pass
        if store.vault_exists():
            self.show_unlock()
        else:
            self.show_welcome()
        try:
            from app.version import APP_VERSION
            from ui.widgets.update_modal import maybe_show_update
            from PySide6.QtCore import QTimer as _Q
            _Q.singleShot(2500, lambda: maybe_show_update(self, APP_VERSION))
        except Exception:
            pass

    # ---- armazon ----
    def _clear_root(self):
        while self.root_lay.count():
            item = self.root_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                _delete_layout(item.layout())
        self.sidebar = None

    def _enter_auth(self, w: QWidget):
        """Auth: columna centrada, max 560, sin sidebar."""
        self._clear_root()
        self.setMinimumSize(380, 600)
        self.resize(*AUTH_SIZE)
        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        box = QWidget()
        box.setMaximumWidth(560)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(w)
        center.addStretch(1)
        center.addWidget(box, 1)
        center.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(center)
        self.root_lay.addWidget(wrap)
        anim.fade_in(box, 200)

    def _enter_app(self):
        """App: sidebar + stack de paginas."""
        from ui.widgets.sidebar import Sidebar
        self._clear_root()
        self.setMinimumSize(*APP_MIN)
        self.resize(*APP_SIZE)
        body = QWidget()
        hl = QHBoxLayout(body)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        self.sidebar = Sidebar()
        self.sidebar.navigated.connect(self._navigate)
        self.sidebar.b_lock.clicked.connect(lambda: self.lock())
        hl.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        hl.addWidget(self.stack, 1)
        self.root_lay.addWidget(body)
        # Paginas persistentes (una sola lista viva, un solo QTimer).
        from ui.screens.accounts import AccountsScreen
        from ui.screens.add import AddScreen
        from ui.screens.prefs import PrefsScreen
        self.scr = AccountsScreen(self)
        self.scr.counts_changed.connect(
            lambda a, b: self.sidebar.set_trash_count(b) if self.sidebar else None)
        self._add = AddScreen(self)
        self._prefs = PrefsScreen(self)
        for p in (self.scr, self._add, self._prefs):
            self.stack.addWidget(p)
        try:
            from app.version import APP_VERSION
            self.sidebar.set_version(APP_VERSION)
        except Exception:
            pass

    def _navigate(self, key: str):
        if key in ("accounts", "trash"):
            self.stack.setCurrentWidget(self.scr)
            self.scr.set_trash_mode(key == "trash")
            self.sidebar.set_active(key)
        elif key == "add":
            self.stack.setCurrentWidget(self._add)
            self.sidebar.set_active("add")
        elif key == "prefs":
            self.stack.setCurrentWidget(self._prefs)
            self._prefs.refresh_stats()
            self.sidebar.set_active("prefs")
        anim.fade_in(self.stack.currentWidget(), 180)
        self._last_active = time.time()

    # ---- navegacion ----
    def show_welcome(self):
        from ui.screens.welcome import WelcomeScreen
        self._enter_auth(WelcomeScreen(self))

    def show_unlock(self):
        from ui.screens.unlock import UnlockScreen
        self._enter_auth(UnlockScreen(self))

    def show_kit(self, code: str, first_time: bool = False):
        from ui.screens.recovery import KitScreen
        self._enter_auth(KitScreen(self, code, first_time))

    def show_recover(self):
        from ui.screens.recovery import KitScreen
        self._enter_auth(KitScreen(self, recover_mode=True))

    def show_accounts(self):
        if self.sidebar is None:
            self._enter_app()
        self._navigate("accounts")
        self.scr.purge_old()

    def show_trash(self):
        if self.sidebar is None:
            self._enter_app()
        self._navigate("trash")

    def show_add(self):
        if self.sidebar is None:
            self._enter_app()
        self._navigate("add")

    def show_prefs(self):
        if self.sidebar is None:
            self._enter_app()
        self._navigate("prefs")

    # ---- bloqueo ----
    def lock(self):
        if self.key is not None:
            vault.wipe(self.key)
            self.key = None
        self.show_unlock()

    def _check_idle(self):
        if self.key is None:
            return
        mins = settings.get_autolock_min()
        if time.time() - self._last_active > mins * 60:
            self.lock()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._last_active = time.time()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        self._last_active = time.time()
        super().keyPressEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        try:
            from PySide6.QtCore import QEvent
            if event.type() == QEvent.WindowStateChange and self.isMinimized():
                if self.key is not None and settings.get_lock_on_minimize():
                    self.lock()
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            watcher = getattr(self, "_session_watcher", None)
            if watcher is not None:
                watcher.stop()
        except Exception:
            pass
        try:
            th = getattr(self, "_update_thread", None)
            if th is not None:
                th.wait(3000)  # el hilo de update nunca bloquea el cierre mas de esto
        except (RuntimeError, Exception):
            pass
        try:
            self._idle.stop()
        except (RuntimeError, Exception):
            pass
        if self.key is not None:
            vault.wipe(self.key)
            self.key = None
        super().closeEvent(event)


def _delete_layout(lay):
    while lay.count():
        item = lay.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _delete_layout(item.layout())
