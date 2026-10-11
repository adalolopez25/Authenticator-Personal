"""Entry point Authenticator. PWM_PROD=1 => flujo real; sin flag => dev con 2 demos."""
from __future__ import annotations

import base64
import logging
import os
import secrets
import sys
import tempfile
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

DEV_USER = "dev"
DEV_MASTER = "Dev-" + secrets.token_hex(8) + "!"


def _dev_bypass():
    """Solo desarrollo: DB temporal + master dev + 2 cuentas demo genericas."""
    from app import auth, store, vault
    tmp = Path(tempfile.mkdtemp(prefix="auth-dev-"))
    store.DATA_DIR = tmp
    store.DB_PATH = tmp / "vault.db"
    key, _kit = auth.create_master(DEV_USER, DEV_MASTER)
    demos = [
        ("Mi Servicio", "usuario@ejemplo.com", "JBSWY3DPEHPK3PXP", 6, 30, "sha1"),
        ("Otro Servicio", "usuario@ejemplo.com", "JBSWY3DPEHPK3PXPAEZA====", 6, 30, "sha1"),
    ]
    for iss, lab, b32, d, p, a in demos:
        clean = "".join(b32.upper().split()).rstrip("=")
        sec = base64.b32decode(clean + "=" * (-len(clean) % 8))
        canon = base64.b32encode(sec).decode().rstrip("=")
        packed = store.pack_secret(canon, d, p, a)
        blobs = {"issuer": vault.encrypt(key, iss.encode()),
                 "label": vault.encrypt(key, lab.encode()),
                 "secret": vault.encrypt(key, packed.encode())}
        store.create_account(blobs)
    log.warning("DEV: sesion temporal en %s (NO es tu boveda real).", tmp)
    return key


def _res(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base.joinpath(*parts)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Authenticator")
    app.setWindowIcon(QIcon(str(_res("assets", "icon.png"))))
    qss = _res("ui", "styles", "theme_dark.qss")
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))
    from ui.main_window import MainWindow
    if os.environ.get("PWM_PROD") == "1" or getattr(sys, "frozen", False):
        w = MainWindow()
    else:
        key = _dev_bypass()
        w = MainWindow()
        w.key = key
        w.show_accounts()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
