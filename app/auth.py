"""Auth: crear master, login con backoff, cambio de master con re-cifrado."""
from __future__ import annotations

import base64
import binascii
import time

from app import recovery, store, vault

VAULT_CHECK_PLAINTEXT = b"VAULT-OK"
_attempts: list[float] = []


def _backoff_delay() -> float:
    n = len(_attempts)
    if n < 5:
        return 0.0
    return float([5, 15, 30, 60][min(n - 5, 3)])


def _failed() -> None:
    _attempts.append(time.time())


def _check_policy(master: str) -> None:
    if len(master) < 12:
        raise ValueError("La clave maestra debe tener al menos 12 caracteres.")
    classes = sum([any(c.islower() for c in master), any(c.isupper() for c in master),
                   any(c.isdigit() for c in master),
                   any(not c.isalnum() for c in master)])
    if classes < 3:
        raise ValueError("Usa al menos 3 de 4 clases: minusculas, mayusculas, digitos, simbolos.")


def create_master(username: str, master: str) -> tuple[bytearray, str]:
    """Crea la boveda y su kit. Devuelve (KEK, codigo_del_kit: mostrar UNA vez)."""
    _check_policy(master)
    salt = vault.generate_salt()
    key = vault.derive_key(master, salt)
    store.meta_set("username", username)
    store.meta_set("master_hash", vault.hash_master(master))
    store.meta_set("salt_kek", base64.b64encode(salt).decode())
    store.meta_set("vault_check", vault.encrypt(key, VAULT_CHECK_PLAINTEXT))
    check, wrap, code = recovery.make_wraps(key)
    store.meta_set("recovery_check", check)
    store.meta_set("recovery_wrap", wrap)
    return key, code


def login(master: str) -> bytearray:
    """Verifica la master y devuelve la KEK. Mensaje generico, sin oraculo."""
    delay = _backoff_delay()
    if delay > 0:
        time.sleep(delay)
    stored = store.meta_get("master_hash")
    salt_b64 = store.meta_get("salt_kek")
    check = store.meta_get("vault_check")
    if stored is None or not vault.verify_master(stored, master):
        _failed()
        raise ValueError("Credenciales incorrectas.")
    try:
        salt = base64.b64decode(salt_b64 or "", validate=True)
    except (binascii.Error, ValueError):
        salt = b""
    if len(salt) != vault.SALT_LEN or not check:
        _failed()
        raise ValueError("Credenciales incorrectas.")
    key = vault.derive_key(master, salt)
    try:
        valido = vault.decrypt(key, check) == VAULT_CHECK_PLAINTEXT
    except ValueError:
        valido = False
    if not valido:
        vault.wipe(key)
        _failed()
        raise ValueError("Credenciales incorrectas.") from None
    _attempts.clear()
    return key


def attempts_left() -> int:
    return max(0, 5 - len(_attempts))


def backoff_delay() -> float:
    return _backoff_delay()


def change_master(old_key: bytes | bytearray, current_master: str,
                  new_master: str) -> bytearray:
    """Cambia la master y re-cifra TODAS las cuentas atomicamente.

    El kit anterior queda invalidado: crear uno nuevo despues.
    """
    stored = store.meta_get("master_hash")
    if stored is None or not vault.verify_master(stored, current_master):
        raise ValueError("La clave actual no es correcta.")
    if current_master == new_master:
        raise ValueError("La nueva clave debe ser diferente.")
    new_key, _ = _recrypt(old_key, new_master, kit="drop")
    vault.wipe(old_key)
    return new_key


def has_recovery() -> bool:
    return bool(store.meta_get("recovery_check") and store.meta_get("recovery_wrap"))


def rotate_recovery(current_master: str) -> str:
    stored = store.meta_get("master_hash")
    if stored is None or not vault.verify_master(stored, current_master):
        raise ValueError("La clave actual no es correcta.")
    try:
        salt = base64.b64decode(store.meta_get("salt_kek") or "", validate=True)
    except (binascii.Error, ValueError):
        salt = b""
    if len(salt) != vault.SALT_LEN:
        raise ValueError("No se pudo crear el kit: boveda ilegible.")
    key = vault.derive_key(current_master, salt)
    try:
        check, wrap, code = recovery.make_wraps(key)
        con = store.connect()
        try:
            con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('recovery_check',?)", (check,))
            con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('recovery_wrap',?)", (wrap,))
            con.commit()
        finally:
            con.close()
        return code
    finally:
        vault.wipe(key)


def recover_with_kit(code: str, new_master: str) -> tuple[bytearray, str]:
    """Recupera con el kit, fija master nueva y emite kit FRESCO."""
    _check_policy(new_master)
    check = store.meta_get("recovery_check")
    wrap = store.meta_get("recovery_wrap")
    if not check or not wrap:
        raise ValueError("No hay kit de recuperación configurado.")
    old_key = recovery.recover_kek(code, check, wrap)
    try:
        new_key, new_code = _recrypt(old_key, new_master, kit="rotate")
    finally:
        vault.wipe(old_key)
    assert new_code is not None
    return new_key, new_code


def _recrypt(old_key: bytes | bytearray, new_master: str,
             kit: str = "drop") -> tuple[bytearray, str | None]:
    _check_policy(new_master)
    rows = store.list_accounts_meta(include_deleted=True)
    plains: list[tuple[str, dict]] = []
    try:
        for r in rows:
            data = {}
            for f in ("issuer", "label", "secret"):
                blob = r.get(f + "_blob", "")
                data[f] = vault.decrypt(old_key, blob).decode("utf-8") if blob else ""
            plains.append((r["id"], data))
    except ValueError as e:
        raise ValueError("Hay registros que no se pueden descifrar: no se ha "
                         "cambiado nada.") from e
    new_salt = vault.generate_salt()
    new_key = vault.derive_key(new_master, new_salt)
    kit_code: str | None = None
    kit_pair: tuple[str, str] | None = None
    if kit == "rotate":
        check2, wrap2, kit_code = recovery.make_wraps(new_key)
        kit_pair = (check2, wrap2)
    con = store.connect()
    try:
        for pid, data in plains:
            blobs = {k: vault.encrypt(new_key, v.encode()) for k, v in data.items()}
            con.execute(
                "UPDATE accounts SET issuer_blob=?,label_blob=?,secret_blob=?,"
                "updated_at=? WHERE id=?",
                (blobs["issuer"], blobs["label"], blobs["secret"],
                 int(time.time()), pid),
            )
        con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('master_hash',?)",
                    (vault.hash_master(new_master),))
        con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('salt_kek',?)",
                    (base64.b64encode(new_salt).decode(),))
        con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('vault_check',?)",
                    (vault.encrypt(new_key, VAULT_CHECK_PLAINTEXT),))
        if kit_pair is not None:
            con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('recovery_check',?)",
                        (kit_pair[0],))
            con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('recovery_wrap',?)",
                        (kit_pair[1],))
        else:
            con.execute("DELETE FROM meta WHERE k IN ('recovery_check','recovery_wrap')")
        con.commit()
    except Exception:
        con.rollback()
        vault.wipe(new_key)
        raise
    finally:
        con.close()
        for _pid, data in plains:
            data.clear()
    return new_key, kit_code
