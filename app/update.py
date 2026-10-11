"""Actualizaciones desde GitHub Releases (unico uso de red permitido, bajo demanda).

Diseno de seguridad:
- Solo HTTPS a api.github.com + objetos githubusercontent (dominio fijo, sin redirects
  a otros hosts: `download` rechaza cambios de host).
- Todo fail-silent: sin red, timeout o JSON inesperado -> UpdateError y la app
  sigue offline como siempre. El chequeo NUNCA bloquea el arranque (va en QThread).
- Opt-out en Preferencias ("Buscar actualizaciones") + "Omitir esta version".
- La actualizacion se instala LANZANDO el Setup oficial del release y cerrando
  la app (un exe en ejecucion no puede reemplazarse a si mismo en Windows).
- Sin dependencias nuevas: solo stdlib (urllib/json/ssl). Nada de `requests`.

Este modulo NO toca la boveda ni la key.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

REPO = "adalolopez25/Authenticator-Personal"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
ALLOWED_HOSTS = {"api.github.com", "objects.githubusercontent.com",
                 "github.com", "release-assets.githubusercontent.com"}
SETUP_ASSET = "Authenticator-Setup.exe"
TIMEOUT_SEC = 12


class UpdateError(Exception):
    """Cualquier fallo de red/parseo. La app lo silencia y sigue offline."""


def parse_version(tag: str) -> tuple[int, ...]:
    """'v1.2.3' -> (1, 2, 3). Acepta con/sin 'v', ignora sufijos ('-rc1', '+b')."""
    t = (tag or "").strip().lstrip("vV")
    core = t.split("-")[0].split("+")[0]
    parts: list[int] = []
    for piece in core.split("."):
        piece = "".join(c for c in piece if c.isdigit())
        if not piece:
            raise UpdateError(f"Versión no válida: {tag!r}")
        parts.append(int(piece))
    if not parts:
        raise UpdateError(f"Versión no válida: {tag!r}")
    return tuple(parts)


def _pad(a: tuple[int, ...], n: int) -> tuple[int, ...]:
    return a + (0,) * (n - len(a))


def is_newer(latest: str, current: str) -> bool:
    """True si `latest` es estrictamente mayor que `current`."""
    try:
        lv, cv = parse_version(latest), parse_version(current)
    except UpdateError:
        return False
    n = max(len(lv), len(cv))
    return _pad(lv, n) > _pad(cv, n)


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Authenticator-Update",
                                               "Accept": "application/vnd.github+json"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC, context=ctx) as r:
            if r.status != 200:
                raise UpdateError(f"HTTP {r.status}")
            try:
                data = json.loads(r.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                raise UpdateError("Respuesta no válida.") from e
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise UpdateError("Sin conexión o tiempo agotado.") from e
    if not isinstance(data, dict):
        raise UpdateError("Respuesta no válida.")
    return data


def _host_of(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return ""


def fetch_latest() -> dict:
    """Devuelve {version, notes, setup_url} del ultimo release. Falla -> UpdateError."""
    data = _get_json(API_LATEST)
    tag = str(data.get("tag_name", ""))
    version = ".".join(str(p) for p in parse_version(tag))  # valida el tag
    notes = str(data.get("body", "") or "")[:2000]
    setup_url = ""
    assets = data.get("assets", [])
    if isinstance(assets, list):
        for a in assets:
            if isinstance(a, dict) and a.get("name") == SETUP_ASSET:
                url = str(a.get("browser_download_url", ""))
                if _host_of(url) in ALLOWED_HOSTS and url.startswith("https://"):
                    setup_url = url
                break
    if not setup_url:
        raise UpdateError("El release no trae instalador.")
    return {"version": version, "notes": notes, "setup_url": setup_url}


def download(url: str, dest: str, progress=None) -> str:
    """Descarga el instalador a `dest`. Rechaza hosts no permitidos y redirects externos."""
    if _host_of(url) not in ALLOWED_HOSTS or not url.startswith("https://"):
        raise UpdateError("Origen de descarga no permitido.")
    ctx = ssl.create_default_context()
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if _host_of(newurl) not in ALLOWED_HOSTS or not newurl.startswith("https://"):
                raise UpdateError("Redirección no permitida.")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(_NoRedirect,
                                            urllib.request.HTTPSHandler(context=ctx))
    req = urllib.request.Request(url, headers={"User-Agent": "Authenticator-Update"})
    try:
        with opener.open(req, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length", 0) or 0)
            done = 0
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    try:
                        progress(done, total)
                    except Exception:
                        pass
    except UpdateError:
        raise
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise UpdateError("Descarga fallida.") from e
    return dest


def launch_installer(path: str) -> None:
    """Lanza el Setup descargado y devuelve (la app debe cerrarse despues)."""
    import subprocess
    try:
        subprocess.Popen([path])
    except OSError as e:
        raise UpdateError(f"No se pudo lanzar el instalador: {e}") from e
