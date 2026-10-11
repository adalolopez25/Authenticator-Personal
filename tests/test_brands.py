"""Brands: iconos + matching por emisor + monograma determinista (sin Qt en proceso)."""
from ui.widgets import brands
from ui.widgets.issuer import color_index, initials


def test_all_brand_names():
    assert len(brands.brand_names()) >= 9


def test_match_brand():
    assert brands.match_brand("GitHub") == "github"
    assert brands.match_brand("Google") == "google"
    assert brands.match_brand("cuenta@gmail.com") == "google"
    assert brands.match_brand("Microsoft") == "microsoft"
    assert brands.match_brand("Outlook personal") == "microsoft"
    assert brands.match_brand("Facebook") == "facebook"
    assert brands.match_brand("Instagram") == "instagram"
    assert brands.match_brand("Twitter") == "x"
    assert brands.match_brand("X") == "x"
    assert brands.match_brand("Twitch") == "twitch"
    assert brands.match_brand("LinkedIn") == "linkedin"
    assert brands.match_brand("Telegram") == "telegram"
    assert brands.match_brand("Mi Banco Raro") is None
    assert brands.match_brand("") is None


def test_monograma_determinista():
    assert color_index("GitHub") == color_index("github")
    assert 0 <= color_index("Cualquiera") < 12
    assert initials("Mi Servicio", "") == "MS"
    assert initials("", "usuario@ejemplo.com") == "UE"
    assert initials("Mi Banco Raro", "") == "MB"
    assert initials("", "") == "?"


def test_art_label_offscreen():
    """Render Qt en subproceso aislado (en pytest el teardown Qt rompe el proceso)."""
    import subprocess
    import sys
    code = (
        "import os; os.environ['QT_QPA_PLATFORM']='offscreen';"
        "from PySide6.QtWidgets import QApplication;"
        "app=QApplication([]);"
        "from ui.widgets.issuer import art_label;"
        "a=art_label('GitHub','',88);"
        "assert a.objectName()=='tileBrand' and not a.pixmap().isNull();"
        "b=art_label('Mi Banco Raro','',88);"
        "assert b.objectName()=='tileMono' and b.text()=='MB';"
        "from ui.widgets.brands import brand_names, brand_icon;"
        "assert all(not brand_icon(n).isNull() for n in brand_names());"
        "a.deleteLater(); b.deleteLater(); del a,b;"
        "app.processEvents(); app.quit(); print('QT_RENDER_OK')"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 0 and "QT_RENDER_OK" in r.stdout, r.stderr[-2000:]
