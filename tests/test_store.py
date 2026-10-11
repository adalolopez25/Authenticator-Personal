"""Store: CRUD cifrado + papelera + reorden + backup roundtrip. Sin secretos reales."""
import tempfile
from pathlib import Path

import pytest

from app import auth, store, vault

MASTER = "Sup3r!Clave-Test-2026"


@pytest.fixture()
def tmpdb(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="auth-test-"))
    monkeypatch.setattr(store, "DATA_DIR", tmp)
    monkeypatch.setattr(store, "DB_PATH", tmp / "vault.db")
    key, _kit = auth.create_master("tester", MASTER)
    yield key
    vault.wipe(key)


def _blobs(key, iss="Mi Servicio", lab="usuario@ejemplo.com"):
    packed = store.pack_secret("JBSWY3DPEHPK3PXP", 6, 30, "sha1")
    return {"issuer": vault.encrypt(key, iss.encode()),
            "label": vault.encrypt(key, lab.encode()),
            "secret": vault.encrypt(key, packed.encode())}


def test_crud_cifrado(tmpdb):
    key = tmpdb
    acc = store.create_account(_blobs(key))
    rows = store.list_accounts_meta()
    assert len(rows) == 1
    # En disco solo blobs v1., nunca plaintext
    raw = store.DB_PATH.read_bytes()
    assert b"Mi Servicio" not in raw and b"JBSWY3DPEHPK3PXP" not in raw
    # Descifra en memoria
    r = store.get_account_meta(acc)
    assert vault.decrypt(key, r["issuer_blob"]).decode() == "Mi Servicio"
    store.update_account(acc, _blobs(key, lab="otra@ejemplo.com"))
    r2 = store.get_account_meta(acc)
    assert vault.decrypt(key, r2["label_blob"]).decode() == "otra@ejemplo.com"


def test_papelera_y_purga(tmpdb):
    key = tmpdb
    acc = store.create_account(_blobs(key))
    store.delete_account(acc)
    assert store.list_accounts_meta() == []
    assert len(store.list_accounts_meta(deleted_only=True)) == 1
    store.restore_account(acc)
    assert len(store.list_accounts_meta()) == 1
    store.delete_account(acc)
    # Purga inmediata (0 dias) la elimina definitivo
    assert store.purge_deleted(older_than_days=-1) >= 1


def test_reorder(tmpdb):
    key = tmpdb
    a = store.create_account(_blobs(key, lab="a@ejemplo.com"))
    b = store.create_account(_blobs(key, lab="b@ejemplo.com"))
    store.reorder([b, a])
    ids = [r["id"] for r in store.list_accounts_meta()]
    assert ids == [b, a]


def test_backup_roundtrip(tmpdb):
    key = tmpdb
    store.create_account(_blobs(key))
    bak = store.export_encrypted()
    assert bak["app"] == "authenticator"
    store.wipe_all()
    assert not store.vault_exists()
    n, _ = store.import_encrypted(bak, merge=False)
    assert n == 1
    # La copia restaurada abre con la misma master
    key2 = auth.login(MASTER)
    vault.wipe(key2)
