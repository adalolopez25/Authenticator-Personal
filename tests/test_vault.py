"""Vault: roundtrip, tag-tamper, KDF determinista, wipe."""
import base64

import pytest

from app import vault


def test_roundtrip():
    salt = vault.generate_salt()
    key = vault.derive_key("Sup3r!Clave-Maestra-2026", salt)
    try:
        blob = vault.encrypt(key, b"hola-mundo")
        assert vault.decrypt(key, blob) == b"hola-mundo"
    finally:
        vault.wipe(key)


def test_tag_tamper_falla_generico():
    salt = vault.generate_salt()
    key = vault.derive_key("Otra!Clave-Segura-1234", salt)
    try:
        blob = vault.encrypt(key, b"secreto")
        raw = base64.b64decode(blob[len("v1."):])
        bad = bytearray(raw)
        bad[-1] ^= 1
        bad_blob = "v1." + base64.b64encode(bytes(bad)).decode()
        with pytest.raises(ValueError, match="datos corruptos o clave incorrecta"):
            vault.decrypt(key, bad_blob)
    finally:
        vault.wipe(key)


def test_kdf_determinista_mismo_salt():
    salt = vault.generate_salt()
    k1 = vault.derive_key("Misma!Clave-12345", salt)
    k2 = vault.derive_key("Misma!Clave-12345", salt)
    try:
        assert bytes(k1) == bytes(k2)
    finally:
        vault.wipe(k1)
        vault.wipe(k2)


def test_wipe_solo_bytearray():
    key = vault.derive_key("Xy!12345678901", vault.generate_salt())
    assert vault.wipe(key) is True
    assert all(b == 0 for b in key)
    assert vault.wipe(b"inmutable") is False
