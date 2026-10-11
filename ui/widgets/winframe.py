"""Marco nativo Windows: titulo oscuro + bloqueo con Win+L/suspender (solo Windows).

Todo fail-silent fuera de Windows. Sin dependencias nuevas (ctypes + Qt).
"""
from __future__ import annotations

import sys


def apply_dark_titlebar(widget) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        dwmapi = ctypes.windll.dwmapi
        for attr in (20, 19):
            try:
                if dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


APP_ID = "Authenticator.BovedaLocal.1"

_WM_WTSSESSION_CHANGE = 0x02B1
_WTS_SESSION_LOCK = 0x7
_WTS_SESSION_LOGOFF = 0x5
_WTS_REMOTE_DISCONNECT = 0x8


class _SessionLockFilter:
    """Filtro nativo: Win+L, logoff o desconexion -> on_lock."""

    def __init__(self, window, on_lock):
        self._window = window
        self._on_lock = on_lock
        self._registered = False
        self._filter = None

    def start(self) -> bool:
        if sys.platform != "win32" or self._registered:
            return self._registered
        try:
            import ctypes
            from PySide6.QtCore import QAbstractNativeEventFilter
            hwnd = int(self._window.winId())
            ok = ctypes.windll.wtsapi32.WTSRegisterSessionNotification(hwnd, 0)
            if not ok:
                return False

            outer = self

            class _Filter(QAbstractNativeEventFilter):
                def nativeEventFilter(self, eventType, message):
                    try:
                        if eventType == "windows_generic_MSG":
                            import ctypes as _c

                            class _MSG(_c.Structure):
                                _fields_ = [
                                    ("hwnd", _c.c_void_p),
                                    ("message", _c.c_uint),
                                    ("wParam", _c.c_size_t),
                                    ("lParam", _c.c_ssize_t),
                                    ("time", _c.c_ulong),
                                    ("x", _c.c_long),
                                    ("y", _c.c_long),
                                ]

                            msg = _c.cast(message, _c.POINTER(_MSG)).contents
                            if msg.message == _WM_WTSSESSION_CHANGE and msg.wParam in (
                                    _WTS_SESSION_LOCK, _WTS_SESSION_LOGOFF,
                                    _WTS_REMOTE_DISCONNECT):
                                outer._on_lock()
                    except Exception:
                        pass
                    return False, 0

            self._filter = _Filter()
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                return False
            app.installNativeEventFilter(self._filter)
            self._registered = True
            return True
        except Exception:
            return False


def watch_session_lock(window, on_lock) -> bool:
    try:
        watcher = _SessionLockFilter(window, on_lock)
        window._session_watcher = watcher
        return watcher.start()
    except Exception:
        return False


def setup_taskbar() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        return True
    except Exception:
        return False
