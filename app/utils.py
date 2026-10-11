"""Utils: clipboard auto-clear (timeout configurable) + aviso historial Win+V."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import settings


def copy_and_clear(text: str, timeout_ms: int | None = None) -> None:
    if timeout_ms is None:
        timeout_ms = settings.get_clipboard_sec() * 1000
    cb = QApplication.clipboard()
    cb.setText(text)
    QTimer.singleShot(timeout_ms, lambda: cb.setText("") if cb.text() == text else None)


def clipboard_history_on() -> bool:
    """Historial de Windows (Win+V) conserva copias fuera de la app. Solo lee registro."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Clipboard") as key:
            value, _ = winreg.QueryValueEx(key, "EnableClipboardHistory")
            return bool(value)
    except Exception:
        return False
