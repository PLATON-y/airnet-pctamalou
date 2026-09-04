"""Tests roundtrip framing AirNet."""

import time

import pytest

from airnet.crypto.keys import generate_or_load_identity
from airnet.crypto.sealed import seal
from airnet.transport.framing import (
    BEACON,
    MAGIC,
    MSG,
    PRESENCE,
    VOICE,
    build_discovery,
    build_sealed,
    decode_length_prefixed,
    encode_length_prefixed,
    node_id_from_pub,
    parse_frame,
)


@pytest.fixture
def alice(tmp_path):
    return generate_or_load_identity(tmp_path / "alice")


@pytest.fixture
def bob(tmp_path):
    return generate_or_load_identity(tmp_path / "bob")


def test_node_id_stable(alice):
    a = node_id_from_pub(alice.public_bytes)
    b = node_id_from_pub(alice.public_bytes)
    assert a == b
    assert len(a) == 16
    assert all(c in "0123456789abcdef" for c in a)


def test_discovery_beacon_roundtrip(alice):
    ts = time.time()
    raw = build_discovery(BEACON, alice.public_bytes, body=b"hi", timestamp=ts)
    assert raw[:4] == MAGIC
    frame = parse_frame(raw)
    assert frame.msg_type == BEACON
    assert frame.node_id == node_id_from_pub(alice.public_bytes)
    assert frame.sender_pub == alice.public_bytes
    assert frame.body == b"hi"
    assert frame.timestamp == int(ts)


def test_discovery_presence(alice):
    raw = build_discovery(PRESENCE, alice.public_bytes)
    frame = parse_frame(raw)
    assert frame.msg_type == PRESENCE
    assert frame.is_discovery


def test_sealed_msg_roundtrip(alice, bob):
    blob = seal(b"bonjour", bob.public_bytes, identity=alice)
    raw = build_sealed(MSG, alice.public_bytes, blob)
    frame = parse_frame(raw)
    assert frame.msg_type == MSG
    assert frame.is_sealed
    assert frame.sender_pub == alice.public_bytes
    assert frame.sealed_blob == blob
    assert frame.node_id == node_id_from_pub(alice.public_bytes)


def test_sealed_voice(alice, bob):
    blob = seal(b"\x00\x01audio", bob.public_bytes, identity=alice)
    frame = parse_frame(build_sealed(VOICE, alice.public_bytes, blob))
    assert frame.msg_type == VOICE


def test_bad_magic():
    with pytest.raises(ValueError, match="magic"):
        parse_frame(b"XXXX\x01" + b"\x00" * 50)


def test_node_id_mismatch(alice):
    raw = bytearray(build_discovery(BEACON, alice.public_bytes))
    # corrupt node_id ascii
    raw[5:8] = b"!!!"
    with pytest.raises(ValueError, match="node_id"):
        parse_frame(bytes(raw))


def test_length_prefixed_roundtrip():
    payload = b"AIR1-test-payload"
    wrapped = encode_length_prefixed(payload)
    out, rest = decode_length_prefixed(wrapped + b"TRAILING")
    assert out == payload
    assert rest == b"TRAILING"


def test_channel_msg_frame():
    from airnet.crypto.channel import seal_channel, derive_channel_key, channel_id_from_name_secret
    from airnet.transport.framing import CHANNEL_MSG, build_channel

    secret = b"y" * 32
    cid = channel_id_from_name_secret("t", secret)
    key = derive_channel_key(secret, cid)
    blob = seal_channel(b"data", key, cid)
    raw = build_channel(cid, blob)
    frame = parse_frame(raw)
    assert frame.msg_type == CHANNEL_MSG
    assert frame.is_channel
    assert not frame.is_sealed
    assert frame.channel_id == cid
    assert frame.channel_blob == blob
