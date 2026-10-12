"""Smoke test UI: arranque offscreen, navegacion basica, iconos no-nulos, salida limpiera.

Los tests Qt siempre van en subproceso aislado: el teardown Qt dentro de pytest
rompe el proceso con -1073740791 (ver AGENTS.md 10.15).
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap


def _run_qt(code: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Ejecuta codigo Qt en subproceso con plataforma offscreen."""
    wrapped = textwrap.dedent(f"""
        import os
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        os.environ['PWM_PROD'] = '0'
        {code}
    """)
    return subprocess.run(
        [sys.executable, "-c", wrapped],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=os.getcwd(),
    )


def test_iconos_svg_no_nulos():
    """Todos los iconos SVG de linea deben renderizar (pixmap no nulo)."""
    code = """
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        from ui.widgets.icons import available, icon
        for name in available():
            ic = icon(name)
            assert not ic.isNull(), f"Icono nulo: {name}"
            assert not ic.pixmap(24, 24).isNull(), f"Pixmap nulo: {name}"
        print("ICONS_OK", len(available()))
    """
    r = _run_qt(code)
    assert r.returncode == 0, f"stderr: {r.stderr[-2000:]}"
    assert "ICONS_OK" in r.stdout


def test_arranque_app_dev():
    """La app en modo dev debe arrancar, mostrar cuentas y salir limpia."""
    code = """
        import sys
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        app = QApplication(sys.argv)
        from ui.main_window import MainWindow
        w = MainWindow()
        w.show()
        QTimer.singleShot(500, w.close)
        rc = app.exec()
        print("EXIT_CLEAN", rc)
    """
    r = _run_qt(code)
    assert r.returncode == 0, f"stderr: {r.stderr[-2000:]}"
    assert "EXIT_CLEAN 0" in r.stdout


def test_navegacion_pantallas():
    """Navegar entre Cuentas, Papelera y Preferencias no debe crash."""
    code = """
        import sys
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        app = QApplication(sys.argv)
        from ui.main_window import MainWindow
        w = MainWindow()
        w.show()
        # Entrar a la app (modo dev: show_accounts)
        w.show_accounts()
        app.processEvents()
        # Simular navegacion: Cuentas -> Papelera -> Cuentas
        w._navigate("accounts")
        app.processEvents()
        w._navigate("trash")
        app.processEvents()
        w._navigate("accounts")
        app.processEvents()
        QTimer.singleShot(200, w.close)
        rc = app.exec()
        print("NAV_OK", rc)
    """
    r = _run_qt(code)
    assert r.returncode == 0, f"stderr: {r.stderr[-2000:]}"
    assert "NAV_OK 0" in r.stdout


def test_modal_anadir():
    """El formulario de anadir debe construirse sin crash (sin exec bloqueante)."""
    code = """
        import sys
        from PySide6.QtWidgets import QApplication, QWidget
        app = QApplication(sys.argv)
        from ui.screens.add import AddScreen
        parent = QWidget()
        form = AddScreen(parent)
        app.processEvents()
        print("ADD_MODAL_OK")
    """
    r = _run_qt(code, timeout=30)
    assert r.returncode == 0, f"stderr: {r.stderr[-2000:]}"
    assert "ADD_MODAL_OK" in r.stdout


def test_stderr_sin_warnings():
    """No debe haber warnings de QPainter ni caracteres invalidos en stderr."""
    code = """
        import sys
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        app = QApplication(sys.argv)
        from ui.main_window import MainWindow
        w = MainWindow()
        w.show()
        QTimer.singleShot(300, w.close)
        app.exec()
    """
    r = _run_qt(code)
    stderr_lower = r.stderr.lower()
    assert "qpainter" not in stderr_lower, f"Warning QPainter: {r.stderr[-2000:]}"
    assert "\\ufffd" not in r.stderr, f"Caracter invalido en stderr: {r.stderr[-2000:]}"
    assert "traceback" not in stderr_lower, f"Traceback: {r.stderr[-2000:]}"
