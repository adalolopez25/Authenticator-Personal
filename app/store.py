"""Store SQLite del Authenticator: guarda SOLO blobs cifrados, nunca plaintext.

Una cuenta = issuer + etiqueta + secreto TOTP (base32 + digits + period + algo
cifrados juntos en `secret_blob`). Nada de red, nada compartido con el gestor.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path


def _default_data_dir() -> Path:
    """En instalado (exe) la boveda vive en %LOCALAPPDATA%; en fuente, ./data."""
    if getattr(sys, "frozen", False):
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "Authenticator" / "data"
        return Path.home() / ".authenticator" / "data"
    return Path(__file__).resolve().parent.parent / "data"


DATA_DIR = _default_data_dir()
DB_PATH = DATA_DIR / "vault.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts(
  id TEXT PRIMARY KEY,
  issuer_blob TEXT NOT NULL DEFAULT '',
  label_blob TEXT NOT NULL DEFAULT '',
  secret_blob TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0,
  deleted_at INTEGER NOT NULL DEFAULT 0
);
"""

#: Claves logicas que acepta cada cuenta (todo cifrado).
BLOB_KEYS = ("issuer", "label", "secret")


def _check_blob_keys(blobs: dict) -> None:
    desconocidas = sorted(set(blobs) - set(BLOB_KEYS))
    if desconocidas:
        raise ValueError(
            f"Claves no validas en blobs: {desconocidas}. Usa {list(BLOB_KEYS)}.")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(DATA_DIR, 0o700)
    except Exception:
        pass


def connect() -> sqlite3.Connection:
    ensure_dirs()
    first = not DB_PATH.exists()
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL;")
    con.executescript(SCHEMA)
    if first:
        try:
            os.chmod(DB_PATH, 0o600)
        except Exception:
            pass
    return con


def vault_exists() -> bool:
    if not DB_PATH.exists():
        return False
    try:
        con = connect()
        row = con.execute("SELECT v FROM meta WHERE k='master_hash'").fetchone()
        con.close()
        return row is not None
    except Exception:
        return False


def meta_get(key: str) -> str | None:
    con = connect()
    row = con.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
    con.close()
    return row[0] if row else None


def meta_set(key: str, value: str) -> None:
    con = connect()
    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (key, value))
    con.commit()
    con.close()


def _next_position(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT COALESCE(MAX(position),-1)+1 FROM accounts").fetchone()
    return int(row[0]) if row else 0


def create_account(blobs: dict) -> str:
    """Crea una cuenta desde blobs YA cifrados. Claves: issuer/label/secret."""
    _check_blob_keys(blobs)
    acc_id = uuid.uuid4().hex
    now = int(time.time())
    con = connect()
    pos = _next_position(con)
    con.execute(
        "INSERT INTO accounts(id,issuer_blob,label_blob,secret_blob,position,"
        "created_at,updated_at,deleted,deleted_at)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (acc_id, blobs.get("issuer", ""), blobs.get("label", ""),
         blobs.get("secret", ""), pos, now, now, 0, 0),
    )
    con.commit()
    con.close()
    return acc_id


def list_accounts_meta(include_deleted: bool = False,
                       deleted_only: bool = False) -> list[dict]:
    """Devuelve SOLO ids + blobs + orden (el descifrado ocurre fuera de store)."""
    con = connect()
    con.row_factory = sqlite3.Row
    q = "SELECT * FROM accounts"
    clauses: list[str] = []
    if deleted_only:
        clauses.append("deleted=1")
    elif not include_deleted:
        clauses.append("deleted=0")
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY position ASC, updated_at DESC"
    rows = con.execute(q).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_account_meta(acc_id: str) -> dict | None:
    con = connect()
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM accounts WHERE id=?", (acc_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def update_account(acc_id: str, blobs: dict) -> None:
    """Reescribe los blobs de una cuenta (item completo, no parche parcial)."""
    _check_blob_keys(blobs)
    con = connect()
    con.execute(
        "UPDATE accounts SET issuer_blob=?,label_blob=?,secret_blob=?,updated_at=?"
        " WHERE id=?",
        (blobs.get("issuer", ""), blobs.get("label", ""), blobs.get("secret", ""),
         int(time.time()), acc_id),
    )
    con.commit()
    con.close()


def rename_account(acc_id: str, issuer_blob: str, label_blob: str) -> None:
    con = connect()
    con.execute("UPDATE accounts SET issuer_blob=?,label_blob=?,updated_at=? WHERE id=?",
                (issuer_blob, label_blob, int(time.time()), acc_id))
    con.commit()
    con.close()


def reorder(ordered_ids: list[str]) -> None:
    """Fija el orden de la lista (drag/reordenar). Solo ids existentes."""
    con = connect()
    for pos, acc_id in enumerate(ordered_ids):
        con.execute("UPDATE accounts SET position=? WHERE id=?", (pos, acc_id))
    con.commit()
    con.close()


def delete_account(acc_id: str) -> None:
    """Borrado SUAVE: papelera 30 dias."""
    con = connect()
    now = int(time.time())
    con.execute("UPDATE accounts SET deleted=1,deleted_at=?,updated_at=? WHERE id=?",
                (now, now, acc_id))
    con.commit()
    con.close()


def restore_account(acc_id: str) -> None:
    con = connect()
    con.execute("UPDATE accounts SET deleted=0,deleted_at=0,updated_at=? WHERE id=?",
                (int(time.time()), acc_id))
    con.commit()
    con.close()


def hard_delete_account(acc_id: str) -> None:
    con = connect()
    con.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
    con.commit()
    con.close()


def purge_deleted(older_than_days: int = 30) -> int:
    cutoff = int(time.time()) - older_than_days * 86400
    con = connect()
    ids = [r[0] for r in con.execute(
        "SELECT id FROM accounts WHERE deleted=1 AND deleted_at<?", (cutoff,)).fetchall()]
    for acc_id in ids:
        con.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
    con.commit()
    con.close()
    return len(ids)


def count_accounts() -> tuple[int, int]:
    """Devuelve (activas, papelera). Solo conteos, sin plaintext."""
    con = connect()
    a = con.execute("SELECT COUNT(*) FROM accounts WHERE deleted=0").fetchone()[0]
    b = con.execute("SELECT COUNT(*) FROM accounts WHERE deleted=1").fetchone()[0]
    con.close()
    return int(a), int(b)


def export_encrypted() -> dict:
    """Copia de seguridad: TODO sigue cifrado (blobs + verificadores)."""
    con = connect()
    con.row_factory = sqlite3.Row
    accounts = [dict(r) for r in con.execute("SELECT * FROM accounts").fetchall()]
    meta = {r[0]: r[1] for r in con.execute("SELECT k,v FROM meta").fetchall()}
    con.close()
    return {"app": "authenticator", "format": 1, "accounts": accounts, "meta": meta}


def import_encrypted(backup: dict, merge: bool = True) -> tuple[int, int]:
    """Restaura una copia cifrada. Devuelve (importados, omitidos)."""
    if not isinstance(backup, dict) or backup.get("app") != "authenticator":
        raise ValueError("Archivo de copia no válido.")
    accounts = backup.get("accounts", [])
    meta = backup.get("meta", {})
    con = connect()
    existing = {r[0] for r in con.execute("SELECT id FROM accounts").fetchall()}
    has_master = con.execute("SELECT v FROM meta WHERE k='master_hash'").fetchone()
    imported = skipped = 0
    try:
        if not has_master:
            for k in ("master_hash", "salt_kek", "vault_check", "username"):
                if k in meta:
                    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (k, meta[k]))
        for it in accounts:
            if not isinstance(it, dict) or not it.get("id"):
                continue
            if it.get("id") in existing and merge:
                skipped += 1
                continue
            con.execute(
                "INSERT OR REPLACE INTO accounts(id,issuer_blob,label_blob,secret_blob,"
                "position,created_at,updated_at,deleted,deleted_at)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (it.get("id"), it.get("issuer_blob", ""), it.get("label_blob", ""),
                 it.get("secret_blob", ""), int(it.get("position", 0)),
                 int(it.get("created_at", 0)), int(it.get("updated_at", 0)),
                 int(it.get("deleted", 0)), int(it.get("deleted_at", 0))),
            )
            imported += 1
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    # Reordena posiciones duplicadas (best-effort).
    rows = list_accounts_meta(include_deleted=True)
    if rows:
        reorder([r["id"] for r in sorted(rows, key=lambda r: (r.get("position", 0)))])
    return imported, skipped


def wipe_all() -> None:
    con = connect()
    con.execute("DELETE FROM accounts")
    con.execute("DELETE FROM meta")
    con.commit()
    con.close()


def shred_file(path, passes: int = 1) -> bool:
    """Tritura un archivo sensible (sobrescribe + borra). Para el origen importado."""
    try:
        from pathlib import Path as _P
        p = _P(path)
        size = p.stat().st_size
        with open(p, "r+b") as f:
            for _ in range(max(1, passes)):
                f.seek(0)
                left = size
                while left > 0:
                    chunk = os.urandom(min(left, 65536))
                    f.write(chunk)
                    left -= len(chunk)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        p.unlink()
        return True
    except Exception:
        return False


def pack_secret(secret_b32: str, digits: int, period: int, algo: str) -> str:
    """Empaqueta los parametros TOTP en un JSON canonico (se cifra como un todo)."""
    return json.dumps({"s": secret_b32, "d": int(digits),
                       "p": int(period), "a": algo}, separators=(",", ":"))


def unpack_secret(raw: str) -> dict:
    """Desempaqueta y valida. Error generico si esta corrupto."""
    try:
        d = json.loads(raw)
        s = str(d.get("s", ""))
        digits = int(d.get("d", 6))
        period = int(d.get("p", 30))
        algo = str(d.get("a", "sha1")).lower()
        if digits not in (6, 7, 8) or period <= 0 or period > 300:
            raise ValueError("bad")
        if algo not in ("sha1", "sha256", "sha512"):
            raise ValueError("bad")
        if not s:
            raise ValueError("bad")
        return {"secret_b32": s, "digits": digits, "period": period, "algo": algo}
    except ValueError:
        raise ValueError("datos corruptos o clave incorrecta") from None
    except Exception:
        raise ValueError("datos corruptos o clave incorrecta") from None
