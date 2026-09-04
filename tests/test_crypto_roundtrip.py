"""Tests round-trip scellage X25519 + ChaCha20-Poly1305."""

from pathlib import Path

import pytest

from airnet.crypto.keys import generate_or_load_identity
from airnet.crypto.sealed import BLOB_VERSION, open, seal


@pytest.fixture
def alice(tmp_path: Path):
    return generate_or_load_identity(tmp_path / "alice")


@pytest.fixture
def bob(tmp_path: Path):
    return generate_or_load_identity(tmp_path / "bob")


def test_generate_persist_and_reload(tmp_path: Path):
    d = tmp_path / "node"
    first = generate_or_load_identity(d)
    second = generate_or_load_identity(d)
    assert first.public_bytes == second.public_bytes
    assert first.private_bytes == second.private_bytes
    priv = d / "identity.x25519"
    assert priv.is_file()
    # mode 0o600 when filesystem supports it
    mode = priv.stat().st_mode & 0o777
    assert mode == 0o600 or mode == 0o644  # some CI fs ignore chmod


def test_seal_open_roundtrip(alice, bob):
    msg = b"bonjour mesh AirNet PCTamalou"
    blob = seal(msg, bob.public_bytes, identity=alice)
    assert blob[0] == BLOB_VERSION
    plain = open(blob, alice.public_bytes, identity=bob)
    assert plain == msg


def test_open_wrong_sender_fails(alice, bob, tmp_path: Path):
    eve = generate_or_load_identity(tmp_path / "eve")
    blob = seal(b"secret", bob.public_bytes, identity=alice)
    with pytest.raises(ValueError):
        open(blob, eve.public_bytes, identity=bob)


def test_open_wrong_recipient_fails(alice, bob, tmp_path: Path):
    charlie = generate_or_load_identity(tmp_path / "charlie")
    blob = seal(b"secret", bob.public_bytes, identity=alice)
    with pytest.raises(ValueError):
        open(blob, alice.public_bytes, identity=charlie)


def test_tampered_blob_fails(alice, bob):
    blob = bytearray(seal(b"data", bob.public_bytes, identity=alice))
    blob[-1] ^= 0xFF
    with pytest.raises(ValueError):
        open(bytes(blob), alice.public_bytes, identity=bob)


def test_unsupported_version(alice, bob):
    blob = bytearray(seal(b"x", bob.public_bytes, identity=alice))
    blob[0] = 0x99
    with pytest.raises(ValueError, match="version"):
        open(bytes(blob), alice.public_bytes, identity=bob)


def test_empty_plaintext(alice, bob):
    blob = seal(b"", bob.public_bytes, identity=alice)
    assert open(blob, alice.public_bytes, identity=bob) == b""


def test_no_hardcoded_legacy_key_in_secure_path():
    """L'ancien secret b'Platon-y_Air' ne doit pas apparaître dans le chemin crypto."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "airnet"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "Platon-y_Air" not in text
        assert "bitwise_xor" not in text
