"""Transport UDP AirNet sur bat0 (ou IP locale pour tests).

Intègre ``airnet.crypto.seal`` / ``open`` pour MSG/VOICE et canaux PSK.
Fonctionne sur ``127.0.0.1`` sans mesh (tests unitaires).

Trust : ``open_sealed_trusted`` refuse les expéditeurs non acceptés (default DENY).
"""

from __future__ import annotations

import logging
import select
import socket
from typing import TYPE_CHECKING, Callable, Optional

from airnet.crypto.keys import Identity
from airnet.crypto.sealed import open as crypto_open
from airnet.crypto.sealed import seal as crypto_seal
from airnet.transport.framing import (
    BEACON,
    CHANNEL_MSG,
    MSG,
    PRESENCE,
    VOICE,
    Frame,
    build_channel,
    build_discovery,
    build_sealed,
    parse_frame,
)

if TYPE_CHECKING:
    from airnet.crypto.channel import ChannelStore
    from airnet.trust.contacts import TrustStore

logger = logging.getLogger("airnet.transport")

DEFAULT_PORT = 41337


class UntrustedSender(Exception):
    """Expéditeur non accepté — message ignoré (default DENY)."""


class UdpTransport:
    """Bind UDP, envoi brut / scellé / canal, réception avec select."""

    def __init__(
        self,
        bind_ip: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        identity: Optional[Identity] = None,
        *,
        broadcast: bool = True,
        trust: Optional[TrustStore] = None,
        channels: Optional[ChannelStore] = None,
    ) -> None:
        self.bind_ip = bind_ip
        self.port = port
        self.identity = identity
        self.broadcast = broadcast
        self.trust = trust
        self.channels = channels
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if broadcast:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind((bind_ip, port))
        self._sock.setblocking(False)
        self._closed = False

    @property
    def sock(self) -> socket.socket:
        return self._sock

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._sock.close()

    def __enter__(self) -> "UdpTransport":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def send_raw(self, data: bytes, addr: tuple[str, int]) -> None:
        self._sock.sendto(data, addr)

    def broadcast_raw(self, data: bytes, port: int | None = None) -> None:
        dest_port = port if port is not None else self.port
        self._sock.sendto(data, ("255.255.255.255", dest_port))

    def send_discovery(
        self,
        msg_type: int = BEACON,
        *,
        body: bytes = b"",
        addr: tuple[str, int] | None = None,
    ) -> bytes:
        """Envoie BEACON/PRESENCE (plaintext). Retourne la trame."""
        if self.identity is None:
            raise RuntimeError("identity requise pour send_discovery")
        frame = build_discovery(msg_type, self.identity.public_bytes, body=body)
        if addr is None:
            self.broadcast_raw(frame)
        else:
            self.send_raw(frame, addr)
        return frame

    def send_sealed(
        self,
        plaintext: bytes,
        recipient_public: bytes,
        *,
        msg_type: int = MSG,
        addr: tuple[str, int],
    ) -> bytes:
        """Scelle et envoie MSG/VOICE vers ``addr``. Retourne la trame."""
        if self.identity is None:
            raise RuntimeError("identity requise pour send_sealed")
        if msg_type not in (MSG, VOICE):
            raise ValueError("send_sealed attend MSG ou VOICE")
        blob = crypto_seal(plaintext, recipient_public, identity=self.identity)
        frame = build_sealed(msg_type, self.identity.public_bytes, blob)
        self.send_raw(frame, addr)
        return frame

    def send_channel(
        self,
        plaintext: bytes,
        *,
        channel_name: str | None = None,
        channel_id: bytes | None = None,
        addr: tuple[str, int] | None = None,
    ) -> bytes:
        """Chiffre avec le secret de canal et envoie CHANNEL_MSG."""
        if self.channels is None:
            raise RuntimeError("ChannelStore requis pour send_channel")
        if channel_name:
            meta = self.channels.get(channel_name)
        elif channel_id is not None:
            meta = self.channels.get(channel_id.hex())
        else:
            raise ValueError("channel_name ou channel_id requis")
        if meta is None:
            raise ValueError("canal inconnu")
        blob = self.channels.encrypt(meta, plaintext)
        frame = build_channel(meta.id_bytes, blob)
        if addr is None:
            self.broadcast_raw(frame)
        else:
            self.send_raw(frame, addr)
        return frame

    def recv_raw(self, timeout: float | None = None) -> tuple[bytes, tuple[str, int]] | None:
        """Reçoit un datagramme. ``None`` si timeout."""
        if timeout is not None:
            ready, _, _ = select.select([self._sock], [], [], timeout)
            if not ready:
                return None
        try:
            data, addr = self._sock.recvfrom(65535)
        except BlockingIOError:
            return None
        return data, addr

    def recv_frame(self, timeout: float | None = None) -> tuple[Frame, tuple[str, int]] | None:
        """Reçoit et parse une trame AirNet."""
        got = self.recv_raw(timeout=timeout)
        if got is None:
            return None
        data, addr = got
        return parse_frame(data), addr

    def open_sealed(self, frame: Frame) -> bytes:
        """Ouvre le blob d'une trame MSG/VOICE avec l'identité locale (sans trust)."""
        if self.identity is None:
            raise RuntimeError("identity requise pour open_sealed")
        if frame.sealed_blob is None:
            raise ValueError("trame sans sealed_blob")
        return crypto_open(frame.sealed_blob, frame.sender_pub, identity=self.identity)

    def open_sealed_trusted(self, frame: Frame) -> bytes:
        """Ouvre MSG/VOICE seulement si ``is_accepted(sender)`` — sinon UntrustedSender."""
        if self.trust is not None and not self.trust.is_accepted(frame.sender_pub):
            logger.info("ignored untrusted sender %s", frame.node_id)
            raise UntrustedSender(frame.node_id)
        return self.open_sealed(frame)

    def open_channel_frame(self, frame: Frame) -> tuple[bytes, str]:
        """Déchiffre CHANNEL_MSG. Retourne (plaintext, channel_name)."""
        if self.channels is None:
            raise RuntimeError("ChannelStore requis")
        if frame.channel_id is None or frame.channel_blob is None:
            raise ValueError("trame sans canal")
        plain = self.channels.decrypt_by_id(frame.channel_id, frame.channel_blob)
        meta = self.channels.get(frame.channel_id.hex())
        name = meta.name if meta else frame.channel_id.hex()[:16]
        return plain, name

    def recv_loop(
        self,
        handler: Callable[[Frame, tuple[str, int]], None],
        *,
        timeout: float = 1.0,
        stop_flag: Callable[[], bool] | None = None,
    ) -> None:
        """Boucle de réception jusqu'à ``stop_flag()`` ou KeyboardInterrupt."""
        while True:
            if stop_flag is not None and stop_flag():
                break
            got = self.recv_frame(timeout=timeout)
            if got is None:
                continue
            frame, addr = got
            handler(frame, addr)
