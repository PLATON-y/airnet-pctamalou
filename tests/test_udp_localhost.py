"""Deux identités échangent un MSG scellé sur 127.0.0.1."""

import threading
import time
from pathlib import Path

import pytest

from airnet.crypto.keys import generate_or_load_identity
from airnet.transport.framing import MSG, node_id_from_pub
from airnet.transport.udp import UdpTransport


def test_sealed_msg_over_localhost(tmp_path: Path):
    alice = generate_or_load_identity(tmp_path / "alice")
    bob = generate_or_load_identity(tmp_path / "bob")

    port_bob = 41338
    port_alice = 41339
    received: list[bytes] = []
    error: list[BaseException] = []

    def bob_listen() -> None:
        try:
            with UdpTransport(
                bind_ip="127.0.0.1",
                port=port_bob,
                identity=bob,
                broadcast=False,
            ) as transport:
                deadline = time.time() + 5.0
                while time.time() < deadline:
                    got = transport.recv_frame(timeout=0.5)
                    if got is None:
                        continue
                    frame, addr = got
                    if frame.msg_type != MSG:
                        continue
                    plain = transport.open_sealed(frame)
                    received.append(plain)
                    assert frame.node_id == node_id_from_pub(alice.public_bytes)
                    assert addr[0] == "127.0.0.1"
                    return
        except BaseException as exc:  # noqa: BLE001 — capture for main thread
            error.append(exc)

    t = threading.Thread(target=bob_listen, daemon=True)
    t.start()
    time.sleep(0.2)

    with UdpTransport(
        bind_ip="127.0.0.1",
        port=port_alice,
        identity=alice,
        broadcast=False,
    ) as transport:
        transport.send_sealed(
            b"hello sealed mesh",
            bob.public_bytes,
            msg_type=MSG,
            addr=("127.0.0.1", port_bob),
        )

    t.join(timeout=6.0)
    if error:
        raise error[0]
    assert received == [b"hello sealed mesh"]
