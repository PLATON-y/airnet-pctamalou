"""Confiance directionnelle : A accepte B, B n'accepte pas A."""

from pathlib import Path

import pytest

from airnet.crypto.keys import generate_or_load_identity
from airnet.crypto.sealed import open, seal
from airnet.trust.contacts import TrustStore


@pytest.fixture
def alice(tmp_path: Path):
    return generate_or_load_identity(tmp_path / "alice_keys")


@pytest.fixture
def bob(tmp_path: Path):
    return generate_or_load_identity(tmp_path / "bob_keys")


def test_trust_directional(alice, bob, tmp_path: Path):
    """A accept B → message B→A s'ouvre ; A→B rejeté côté B (non accepté)."""
    trust_a = TrustStore(tmp_path / "trust_a")
    trust_b = TrustStore(tmp_path / "trust_b")

    # A accepte B uniquement
    trust_a.accept_peer(bob.public_bytes, display_name="Bob")
    assert trust_a.is_accepted(bob.public_bytes) is True
    assert trust_b.is_accepted(alice.public_bytes) is False

    # B → A : A a accepté B → ouverture OK
    blob_b_to_a = seal(b"salut de Bob", alice.public_bytes, identity=bob)
    assert trust_a.is_accepted(bob.public_bytes)
    plain = open(blob_b_to_a, bob.public_bytes, identity=alice)
    assert plain == b"salut de Bob"

    # A → B : B n'a pas accepté A → politique refuse (avant même open)
    blob_a_to_b = seal(b"salut de Alice", bob.public_bytes, identity=alice)
    assert trust_b.is_accepted(alice.public_bytes) is False
    # simulate receive policy
    if not trust_b.is_accepted(alice.public_bytes):
        rejected = True
    else:
        open(blob_a_to_b, alice.public_bytes, identity=bob)
        rejected = False
    assert rejected is True

    # Après acceptation mutuelle, A→B fonctionne
    trust_b.accept_peer(alice.public_bytes)
    assert trust_b.is_accepted(alice.public_bytes)
    assert open(blob_a_to_b, alice.public_bytes, identity=bob) == b"salut de Alice"


def test_revoke(alice, bob, tmp_path: Path):
    store = TrustStore(tmp_path / "trust")
    store.accept_peer(bob.public_bytes)
    assert store.is_accepted(bob.public_bytes)
    assert store.revoke_peer(bob.public_bytes) is True
    assert store.is_accepted(bob.public_bytes) is False


def test_persist_reload(alice, bob, tmp_path: Path):
    d = tmp_path / "trust_persist"
    s1 = TrustStore(d)
    s1.accept_peer(bob.public_bytes, display_name="Bob")
    s2 = TrustStore(d)
    assert s2.is_accepted(bob.public_bytes)
    assert s2.list_accepted()[0].display_name == "Bob"
