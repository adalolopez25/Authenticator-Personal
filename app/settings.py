"""Preferencias no secretas (tabla meta). Los secretos NUNCA van aqui."""
from __future__ import annotations

from app import store

DEFAULT_AUTOLOCK_MIN = 3
DEFAULT_CLIPBOARD_SEC = 15


def _get_int(key: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(store.meta_get(key) or default)))
    except (TypeError, ValueError):
        return default


def get_autolock_min() -> int:
    return _get_int("autolock_min", DEFAULT_AUTOLOCK_MIN, 1, 30)


def set_autolock_min(minutes: int) -> None:
    store.meta_set("autolock_min", str(max(1, min(30, int(minutes)))))


def get_clipboard_sec() -> int:
    return _get_int("clipboard_sec", DEFAULT_CLIPBOARD_SEC, 5, 120)


def set_clipboard_sec(seconds: int) -> None:
    store.meta_set("clipboard_sec", str(max(5, min(120, int(seconds)))))


def _get_bool(key: str, default: bool) -> bool:
    return (store.meta_get(key) or ("1" if default else "0")) == "1"


def set_bool(key: str, value: bool) -> None:
    store.meta_set(key, "1" if value else "0")


def get_lock_on_minimize() -> bool:
    return _get_bool("lock_on_minimize", True)


def set_lock_on_minimize(value: bool) -> None:
    set_bool("lock_on_minimize", value)


def get_reduced_motion() -> bool:
    return _get_bool("reduced_motion", False)


def set_reduced_motion(value: bool) -> None:
    set_bool("reduced_motion", value)


def get_last_backup() -> str | None:
    return store.meta_get("last_backup")


def set_last_backup(label: str) -> None:
    store.meta_set("last_backup", label)


def get_auto_update() -> bool:
    return _get_bool("auto_update", True)


def set_auto_update(value: bool) -> None:
    set_bool("auto_update", value)


def get_skipped_version() -> str | None:
    return store.meta_get("skipped_version")


def set_skipped_version(version: str) -> None:
    store.meta_set("skipped_version", version)
