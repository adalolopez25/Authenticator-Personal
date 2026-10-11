"""Auth: crear/login/backoff/kit/rotate. Sin secretos reales."""
import tempfile
from pathlib import Path

import pytest

from app import auth, store, vault

MASTER = "Sup3r!Clave-Test-2026"
NEW = "Nu3va!Clave-Test-2026"


@pytest.fixture()
def tmpdb(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="auth-test-"))
    monkeypatch.setattr(store, "DATA_DIR", tmp)
    monkeypatch.setattr(store, "DB_PATH", tmp / "vault.db")
    auth._attempts.clear()
    yield tmp
    auth._attempts.clear()


def test_create_y_login(tmpdb):
    key, code = auth.create_master("yo", MASTER)
    assert code and "-" in code
    vault.wipe(key)
    key2 = auth.login(MASTER)
    vault.wipe(key2)


def test_backoff_tras_5_fallos(tmpdb):
    auth.create_master("yo", MASTER)
    for _ in range(5):
        with pytest.raises(ValueError):
            auth.login("clave-incorrecta-123!")
    assert auth.attempts_left() == 0
    assert auth.backoff_delay() > 0


def test_kit_recupera_y_rota(tmpdb):
    key, code = auth.create_master("yo", MASTER)
    acc_blobs = {"issuer": vault.encrypt(key, b"Mi Servicio"),
                 "label": vault.encrypt(key, b"cuenta"),
                 "secret": vault.encrypt(key, store.pack_secret(
                     "JBSWY3DPEHPK3PXP", 6, 30, "sha1").encode())}
    store.create_account(acc_blobs)
    vault.wipe(key)
    new_key, fresh = auth.recover_with_kit(code, NEW)
    assert fresh and fresh != code
    vault.wipe(new_key)
    # Login con la nueva abre; kit viejo ya no sirve
    k2 = auth.login(NEW)
    vault.wipe(k2)
    with pytest.raises(ValueError):
        auth.recover_with_kit(code, MASTER)


def test_change_master_recifra(tmpdb):
    key, _k = auth.create_master("yo", MASTER)
    acc = store.create_account({"issuer": vault.encrypt(key, b"S"),
                                "label": vault.encrypt(key, b"L"),
                                "secret": vault.encrypt(key, store.pack_secret(
                                    "JBSWY3DPEHPK3PXP", 6, 30, "sha1").encode())})
    new_key = auth.change_master(key, MASTER, NEW)
    r = store.get_account_meta(acc)
    assert vault.decrypt(new_key, r["issuer_blob"]) == b"S"
    vault.wipe(new_key)
