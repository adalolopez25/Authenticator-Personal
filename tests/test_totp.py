"""Vectores RFC 6238/4226 (SHA-1/256/512, 8 digitos) + parseo otpauth."""
import base64

from app import totp

# Secreto RFC 6238: ASCII "12345678901234567890" (SHA1), etc.
RFC_SHA1 = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
RFC_SHA256 = base64.b32encode(b"12345678901234567890123456789012").decode().rstrip("=")
RFC_SHA512 = base64.b32encode(
    b"1234567890123456789012345678901234567890123456789012345678901234").decode().rstrip("=")

VECTORS = [
    # (t, sha1, sha256, sha512) — RFC 6238 apendice B, 8 digitos, periodo 30
    (59, "94287082", "46119246", "90693936"),
    (1111111109, "07081804", "68084774", "25091201"),
    (1111111111, "14050471", "67062674", "99943326"),
    (1234567890, "89005924", "91819424", "93441116"),
    (2000000000, "69279037", "90698825", "38618901"),
    (20000000000, "65353130", "77737706", "47863826"),
]


def _raw(b32: str) -> bytes:
    return base64.b32decode(b32 + "=" * (-len(b32) % 8))


def test_rfc_vectors():
    raws = {"sha1": _raw(RFC_SHA1), "sha256": _raw(RFC_SHA256), "sha512": _raw(RFC_SHA512)}
    for t, s1, s256, s512 in VECTORS:
        assert totp.generate(raws["sha1"], at=t, digits=8, period=30, algo="sha1") == s1
        assert totp.generate(raws["sha256"], at=t, digits=8, period=30, algo="sha256") == s256
        assert totp.generate(raws["sha512"], at=t, digits=8, period=30, algo="sha512") == s512


def test_parse_uri_full():
    uri = (f"otpauth://totp/Mi Servicio:usuario@ejemplo.com?secret={RFC_SHA1}"
           "&issuer=Mi Servicio&digits=6&period=30&algorithm=SHA1")
    p = totp.parse_uri(uri)
    assert p["issuer"] == "Mi Servicio"
    assert p["digits"] == 6 and p["period"] == 30 and p["algo"] == "sha1"
    code = totp.generate(p["secret"], at=59, digits=6, period=30)
    assert len(code) == 6 and code.isdigit()


def test_parse_secret_loose():
    secret, d, per = totp.parse_secret("jbsw y3dp ehpk 3pxp")
    assert d == 6 and per == 30 and len(secret) >= 10


def test_bad_inputs():
    import pytest
    for bad in ["", "!!!!", "otpauth://totp/x?secret=AAA", "JBSW"]:
        with pytest.raises(ValueError):
            totp.parse_any(bad)
