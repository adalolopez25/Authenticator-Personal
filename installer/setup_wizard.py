"""Instalador de Authenticator para Windows (wizard ES).

Paginas: Bienvenida -> Carpeta -> Opciones -> Instalando -> Fin.
La boveda (%LOCALAPPDATA%\\Authenticator\\data) JAMAS se toca.
Solo stdlib + PySide6.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
                               QWizard, QWizardPage)

APP_NAME = "Authenticator"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Authenticator"

try:
    from app.version import APP_VERSION
except Exception:
    APP_VERSION = "?"


def _res(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def default_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(local) / "Authenticator"


def _run_hidden(*args: str) -> bool:
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        r = subprocess.run(list(args), capture_output=True, timeout=60,
                           creationflags=flags)
        return r.returncode == 0
    except Exception:
        return False


def make_shortcut(lnk: Path, target: Path, workdir: Path) -> bool:
    try:
        lnk.parent.mkdir(parents=True, exist_ok=True)
        ps = ("$ws = New-Object -ComObject WScript.Shell; "
              f"$s = $ws.CreateShortcut('{lnk}'); "
              f"$s.TargetPath = '{target}'; "
              f"$s.WorkingDirectory = '{workdir}'; "
              f"$s.IconLocation = '{target},0'; $s.Save()")
        return _run_hidden("powershell", "-NoProfile", "-NonInteractive",
                           "-ExecutionPolicy", "Bypass", "-Command", ps) and lnk.exists()
    except Exception:
        return False


def desktop_dir() -> Path | None:
    for cand in (os.environ.get("USERPROFILE"), str(Path.home())):
        if cand:
            d = Path(cand) / "Desktop"
            if d.is_dir():
                return d
    return None


def startmenu_dir() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Authenticator"


def register_uninstall(target: Path, version: str) -> bool:
    try:
        import winreg
        exe = target / "Authenticator.exe"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Bóveda local")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(target))
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{exe},0")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                              f'"{target / "Uninstall.exe"}" --uninstall --dir "{target}"')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        return True
    except Exception:
        return False


def unregister() -> None:
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    except Exception:
        pass


def do_install(target: Path, shortcuts: bool, log) -> bool:
    payload = _res("payload", "Authenticator.exe")
    if not payload.exists():
        log("No se encontró el programa dentro del instalador.")
        return False
    try:
        target.mkdir(parents=True, exist_ok=True)
        log("Copiando programa…")
        shutil.copy2(str(payload), str(target / "Authenticator.exe"))
        log("Registrando desinstalador…")
        here = Path(sys.argv[0]).resolve()
        try:
            shutil.copy2(str(here), str(target / "Uninstall.exe"))
        except Exception as e:
            log(f"Aviso: no se pudo copiar Uninstall.exe ({e})")
        if shortcuts:
            log("Creando accesos directos…")
            exe = target / "Authenticator.exe"
            desk = desktop_dir()
            if desk is not None:
                make_shortcut(desk / "Authenticator.lnk", exe, target)
            menu = startmenu_dir()
            if menu is not None:
                make_shortcut(menu / "Authenticator.lnk", exe, target)
        log("Registrando en el sistema…")
        register_uninstall(target, APP_VERSION)
        log("Listo.")
        return True
    except Exception as e:
        log(f"Error: {e}")
        return False


def do_uninstall(target: Path, log) -> bool:
    """Quita programa y accesos. LA BOVEDA (data/) SE CONSERVA."""
    try:
        log("Quitando accesos directos…")
        desk = desktop_dir()
        if desk is not None:
            try:
                (desk / "Authenticator.lnk").unlink(missing_ok=True)
            except Exception:
                pass
        menu = startmenu_dir()
        if menu is not None:
            try:
                (menu / "Authenticator.lnk").unlink(missing_ok=True)
                menu.rmdir()
            except Exception:
                pass
        log("Quitando registro…")
        unregister()
        log("Borrando programa (la bóveda se conserva)…")
        for name in ("Authenticator.exe", "Uninstall.exe"):
            try:
                (target / name).unlink(missing_ok=True)
            except Exception:
                pass
        try:
            target.rmdir()
        except Exception:
            pass
        log("Desinstalación completa. Tus datos siguen en data/.")
        return True
    except Exception as e:
        log(f"Error: {e}")
        return False


class _Page(QWizardPage):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self.setTitle(title)
        self.setSubTitle(subtitle)


class SetupWizard(QWizard):
    def __init__(self, target: Path, no_shortcuts: bool = False):
        super().__init__()
        self.setWindowTitle(f"Instalación de {APP_NAME} {APP_VERSION}")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.BackButton, "< Atrás")
        self.setButtonText(QWizard.NextButton, "Siguiente >")
        self.setButtonText(QWizard.CommitButton, "Instalar")
        self.setButtonText(QWizard.FinishButton, "Terminar")
        self.setButtonText(QWizard.CancelButton, "Cancelar")
        self.setMinimumSize(640, 460)
        self._target = target
        self._shortcuts = not no_shortcuts
        self._ok = False

        welcome = _Page("Bienvenido", f"Este asistente instalará {APP_NAME} en tu equipo.")
        wl = QVBoxLayout(welcome)
        info = QLabel("Autenticador TOTP local (AES-256-GCM + Argon2id). Sin cuentas, sin nube.\n\n"
                      "Pulsa Siguiente para continuar.")
        info.setWordWrap(True)
        wl.addWidget(info)

        folder = _Page("Carpeta de instalación", "El programa vive aquí; tu bóveda irá a data/ dentro de ella.")
        fl = QVBoxLayout(folder)
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(str(target))
        browse = QPushButton("Examinar…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(browse)
        fl.addLayout(row)
        fl.addStretch(1)
        folder.registerField("destino*", self.dir_edit)

        opts = _Page("Opciones", "Accesos directos y arranque.")
        ol = QVBoxLayout(opts)
        self.chk_desk = QCheckBox("Acceso directo en el escritorio")
        self.chk_menu = QCheckBox("Acceso directo en el menú inicio")
        self.chk_run = QCheckBox("Abrir Authenticator al terminar")
        for c in (self.chk_desk, self.chk_menu, self.chk_run):
            c.setChecked(True)
        if no_shortcuts:
            self.chk_desk.setChecked(False)
            self.chk_menu.setChecked(False)
        for c in (self.chk_desk, self.chk_menu, self.chk_run):
            ol.addWidget(c)
        ol.addStretch(1)

        self.prog_page = _Page("Instalando", "Copiando archivos…")
        self.prog_page.setCommitPage(True)
        pl = QVBoxLayout(self.prog_page)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.status = QLabel("Preparando…")
        self.status.setWordWrap(True)
        pl.addWidget(self.bar)
        pl.addWidget(self.status)
        pl.addStretch(1)

        done = _Page("Completado", "La instalación terminó.")
        dl = QVBoxLayout(done)
        self.done_lbl = QLabel("")
        self.done_lbl.setWordWrap(True)
        dl.addWidget(self.done_lbl)
        dl.addStretch(1)

        for p in (welcome, folder, opts, self.prog_page, done):
            self.addPage(p)
        self.currentIdChanged.connect(self._entered)

    def _browse(self):
        from PySide6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(self, "Carpeta de instalación",
                                             self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def _entered(self, idx: int):
        if self.page(idx) is self.prog_page and not self._ok:
            self._run_install()

    def _run_install(self):
        target = Path(self.field("destino"))
        self._shortcuts = self.chk_desk.isChecked() or self.chk_menu.isChecked()
        self.backButton().setEnabled(False)
        msgs: list[str] = []
        ok = do_install(target, self._shortcuts,
                        lambda m: (msgs.append(m), self.status.setText(m),
                                   QApplication.processEvents()))
        self.bar.setRange(0, 1)
        self.bar.setValue(1 if ok else 0)
        self._ok = ok
        self._target = target
        if ok:
            self.done_lbl.setText(f"{APP_NAME} quedó instalado en:\n{target}\n\n"
                                  "Tu bóveda se creará en data/ al abrirlo por primera vez.")
        else:
            self.done_lbl.setText("La instalación falló:\n" + "\n".join(msgs))
        self.backButton().setEnabled(True)
        if ok:
            self.next()

    def accept(self):
        if self._ok and getattr(self, "chk_run", None) is not None and self.chk_run.isChecked():
            try:
                import subprocess as _sp
                _sp.Popen([str(self._target / "Authenticator.exe")])
            except Exception:
                pass
        super().accept()


def main(argv: list[str]) -> int:
    args = argv[1:]
    target = Path(next((a.split("=", 1)[1] for a in args if a.startswith("--dir=")),
                        default_dir()))
    for i, a in enumerate(args):
        if a == "--dir" and i + 1 < len(args):
            target = Path(args[i + 1])
    if "--uninstall" in args:
        ok = do_uninstall(target, print)
        if "--quiet" not in args and not any(a.startswith("--dir") for a in args):
            app = QApplication([])
            QMessageBox.information(None, APP_NAME,
                                    "Desinstalación completa." if ok else "Falló la desinstalación.")
        return 0 if ok else 1
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    ico = _res("assets", "icon.png")
    if ico.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(ico)))
    qss = _res("ui", "styles", "theme_dark.qss")
    if qss.exists():
        try:
            app.setStyleSheet(qss.read_text(encoding="utf-8"))
        except Exception:
            pass
    wiz = SetupWizard(target, no_shortcuts="--no-shortcuts" in args)
    wiz.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
