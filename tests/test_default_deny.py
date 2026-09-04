"""Default DENY : expéditeur inconnu / non accepté → message droppé."""

from pathlib import Path

import pytest

from airnet.crypto.keys import generate_or_load_identity
from airnet.crypto.sealed import seal
from airnet.transport.framing import MSG, build_sealed, parse_frame
from airnet.transport.udp import UntrustedSender, UdpTransport
from airnet.trust.contacts import TrustStore


def test_default_deny_unknown_sender(tmp_path: Path):
    alice = generate_or_load_identity(tmp_path / "alice")
    bob = generate_or_load_identity(tmp_path / "bob")
    eve = generate_or_load_identity(tmp_path / "eve")

    trust_bob = TrustStore(tmp_path / "trust_bob")
    # Bob n'accepte personne

    # Eve scelle un message pour Bob
    blob = seal(b"spam", bob.public_bytes, identity=eve)
    frame = parse_frame(build_sealed(MSG, eve.public_bytes, blob))

    transport = UdpTransport(
        bind_ip="127.0.0.1",
        port=0,  # ephemeral — may fail on some systems; we only need open_sealed_trusted
        identity=bob,
        broadcast=False,
        trust=trust_bob,
    )
    try:
        # Re-bind note: port=0 gives ephemeral; fine for unit test of open policy
        with pytest.raises(UntrustedSender):
            transport.open_sealed_trusted(frame)
    finally:
        transport.close()


def test_default_deny_then_accept(tmp_path: Path):
    alice = generate_or_load_identity(tmp_path / "alice")
    bob = generate_or_load_identity(tmp_path / "bob")
    trust_bob = TrustStore(tmp_path / "trust_bob")

    blob = seal(b"hello", bob.public_bytes, identity=alice)
    frame = parse_frame(build_sealed(MSG, alice.public_bytes, blob))

    transport = UdpTransport(
        bind_ip="127.0.0.1",
        port=0,
        identity=bob,
        broadcast=False,
        trust=trust_bob,
    )
    try:
        with pytest.raises(UntrustedSender):
            transport.open_sealed_trusted(frame)

        trust_bob.accept_peer(alice.public_bytes)
        plain = transport.open_sealed_trusted(frame)
        assert plain == b"hello"
    finally:
        transport.close()


def test_is_accepted_false_by_default(tmp_path: Path):
    store = TrustStore(tmp_path / "empty")
    fake_pub = b"\x11" * 32
    assert store.is_accepted(fake_pub) is False
    assert store.list_accepted() == []
