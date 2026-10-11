"""MainWindow compacta vertical: auth 420x640, app 380x620. Sin sidebars."""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from app import settings, store, vault
from ui.styles import animations as anim
from ui.widgets.icons import icon


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.key: bytearray | None = None
        self._last_active = time.time()
        self.setWindowTitle("Authenticator")
        self.resize(420, 640)
        self.setMinimumSize(340, 520)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        # Topbar minima: titulo + lock + gear
        top = QWidget()
        top.setObjectName("sidebar")
        hl = QHBoxLayout(top)
        hl.setContentsMargins(12, 8, 12, 8)
        title = QLabel("Authenticator")
        title.setStyleSheet("font-weight: 700; font-size: 14px;")
        hl.addWidget(title, 1)
        self.b_lock = QPushButton()
        self.b_lock.setObjectName("toolBtn")
        self.b_lock.setIcon(icon("lock"))
        self.b_lock.setToolTip("Bloquear")
        self.b_lock.clicked.connect(lambda: self.lock())
        self.b_prefs = QPushButton()
        self.b_prefs.setObjectName("toolBtn")
        self.b_prefs.setIcon(icon("gear"))
        self.b_prefs.setToolTip("Preferencias")
        self.b_prefs.clicked.connect(lambda: self.show_prefs())
        hl.addWidget(self.b_lock)
        hl.addWidget(self.b_prefs)
        lay.addWidget(top)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
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
        # Pantalla inicial
        if store.vault_exists():
            self.show_unlock()
        else:
            self.show_welcome()

    # ---- navegacion ----
    def _set(self, w: QWidget, app_mode: bool):
        while self.stack.count():
            old = self.stack.widget(0)
            self.stack.removeWidget(old)
            old.deleteLater()
        self.stack.addWidget(w)
        self._last_active = time.time()
        self.resize(380, 620) if app_mode else self.resize(420, 640)
        has_key = self.key is not None
        self.b_lock.setVisible(has_key)
        self.b_prefs.setVisible(has_key and app_mode)

    def show_welcome(self):
        from ui.screens.welcome import WelcomeScreen
        self._set(WelcomeScreen(self), app_mode=False)

    def show_unlock(self):
        from ui.screens.unlock import UnlockScreen
        self._set(UnlockScreen(self), app_mode=False)

    def show_kit(self, code: str, first_time: bool = False):
        from ui.screens.recovery import KitScreen
        self._set(KitScreen(self, code, first_time), app_mode=False)

    def show_recover(self):
        from ui.screens.recovery import KitScreen
        self._set(KitScreen(self, recover_mode=True), app_mode=False)

    def show_accounts(self):
        from ui.screens.accounts import AccountsScreen
        self.scr = AccountsScreen(self)
        self._set(self.scr, app_mode=True)
        self.scr.reload()
        self.scr.purge_old()

    def show_add(self):
        from ui.screens.add import AddScreen
        self._set(AddScreen(self), app_mode=True)

    def show_prefs(self):
        from ui.screens.prefs import PrefsScreen
        self._set(PrefsScreen(self), app_mode=True)

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
        if self.key is not None:
            vault.wipe(self.key)
            self.key = None
        super().closeEvent(event)
