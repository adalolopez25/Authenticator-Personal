"""Update: comparacion de versiones y parseo del release. Sin red real (mock)."""
import pytest

from app import update


def test_parse_version():
    assert update.parse_version("v1.2.3") == (1, 2, 3)
    assert update.parse_version("1.0.0") == (1, 0, 0)
    assert update.parse_version("V2.10") == (2, 10)
    assert update.parse_version("1.0.0-rc1") == (1, 0, 0)
    with pytest.raises(update.UpdateError):
        update.parse_version("no-version")


def test_is_newer():
    assert update.is_newer("1.0.1", "1.0.0")
    assert update.is_newer("1.1", "1.0.9")
    assert update.is_newer("2.0.0", "1.9.9")
    assert not update.is_newer("1.0.0", "1.0.0")
    assert not update.is_newer("1.0.0", "1.0.1")
    assert not update.is_newer("v1.0.0", "1.0.0")
    assert not update.is_newer("basura", "1.0.0")


def test_fetch_latest_parse(monkeypatch):
    fake = {"tag_name": "v1.2.0", "body": "Notas",
            "assets": [{"name": "Authenticator-Setup.exe",
                        "browser_download_url": "https://objects.githubusercontent.com/x/Authenticator-Setup.exe"}]}

    class _R:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            import json
            return json.dumps(fake).encode()

    monkeypatch.setattr(update.urllib.request, "urlopen", lambda *a, **k: _R())
    info = update.fetch_latest()
    assert info["version"] == "1.2.0" and info["notes"] == "Notas"
    assert info["setup_url"].endswith("Authenticator-Setup.exe")


def test_fetch_rechaza_sin_instalador(monkeypatch):
    fake = {"tag_name": "v1.2.0", "body": "", "assets": []}

    class _R:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            import json
            return json.dumps(fake).encode()

    monkeypatch.setattr(update.urllib.request, "urlopen", lambda *a, **k: _R())
    with pytest.raises(update.UpdateError):
        update.fetch_latest()


def test_download_rechaza_host():
    with pytest.raises(update.UpdateError):
        update.download("https://ejemplo-malicioso.com/x.exe", "nada.exe")
    with pytest.raises(update.UpdateError):
        update.download("http://api.github.com/x.exe", "nada.exe")
