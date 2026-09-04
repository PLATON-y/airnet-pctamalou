"""Framing AirNet — formats filaires UDP.

Wire format
-----------
Préfixe commun : ``MAGIC (4) = b"AIR1"`` puis ``type_u8``.

**Découverte (BEACON=1, PRESENCE=2)** — plaintext, pas de secret :

    AIR1 | type_u8 | node_id_ascii16 | public_key_32 | timestamp_u64_be
         | body_len_u16_be | body_bytes

``node_id`` = ``sha256(public_key).hexdigest()[:16]`` (16 caractères ASCII hex).
Aucun chiffrement revendiqué sur ces trames : la clé publique est volontairement
exposée pour la découverte de pairs.

**Unicast MSG=3 / VOICE=4** — scellé avec ``airnet.crypto.seal`` :

    AIR1 | type_u8 | sender_pub_32 | sealed_blob

où ``sealed_blob = seal(plaintext, recipient_pub)``. Le destinataire lit
``sender_pub`` en clair puis appelle ``open(sealed_blob, sender_pub)`` **uniquement
si** le pair est accepté (trust store — default DENY).

**Canal PSK CHANNEL_MSG=5** — secret partagé OOB (pair ou groupe) :

    AIR1 | 5 | channel_id_16 | channel_blob

où ``channel_blob = version | nonce | ct||tag`` (ChaCha20-Poly1305, AAD = version|channel_id).
Membership = connaître le secret. Pas d'ECDH.

Types
-----
- BEACON = 1
- PRESENCE = 2
- MSG = 3
- VOICE = 4
- CHANNEL_MSG = 5

Les helpers ``encode_length_prefixed`` / ``decode_length_prefixed`` encapsulent
un payload avec préfixe ``u32`` big-endian (utile hors UDP datagramme unique).
"""

from __future__ import annotations

import hashlib
import struct
import time
from dataclasses import dataclass
from typing import Optional

MAGIC = b"AIR1"
BEACON = 1
PRESENCE = 2
MSG = 3
VOICE = 4
CHANNEL_MSG = 5

TYPE_NAMES = {
    BEACON: "BEACON",
    PRESENCE: "PRESENCE",
    MSG: "MSG",
    VOICE: "VOICE",
    CHANNEL_MSG: "CHANNEL_MSG",
}

DISCOVERY_TYPES = frozenset({BEACON, PRESENCE})
SEALED_TYPES = frozenset({MSG, VOICE})
CHANNEL_TYPES = frozenset({CHANNEL_MSG})

NODE_ID_LEN = 16
PUB_LEN = 32
CHANNEL_ID_LEN = 16
HEADER_DISCOVERY = 4 + 1 + NODE_ID_LEN + PUB_LEN + 8 + 2  # + body_len


def node_id_from_pub(public_key: bytes) -> str:
    """Identifiant nœud : 16 hex du SHA-256 de la clé publique X25519."""
    if len(public_key) != PUB_LEN:
        raise ValueError("public_key doit faire 32 octets")
    return hashlib.sha256(public_key).hexdigest()[:NODE_ID_LEN]


def encode_length_prefixed(payload: bytes) -> bytes:
    """``u32_be length | payload``."""
    return struct.pack("!I", len(payload)) + payload


def decode_length_prefixed(data: bytes) -> tuple[bytes, bytes]:
    """Retourne ``(payload, remainder)``."""
    if len(data) < 4:
        raise ValueError("trame trop courte pour length-prefix")
    (length,) = struct.unpack("!I", data[:4])
    if len(data) < 4 + length:
        raise ValueError("length-prefix incohérent")
    return data[4 : 4 + length], data[4 + length :]


@dataclass
class Frame:
    """Trame AirNet parsée."""

    msg_type: int
    sender_pub: bytes = b""
    node_id: str = ""
    timestamp: Optional[float] = None
    body: bytes = b""
    sealed_blob: Optional[bytes] = None
    channel_id: Optional[bytes] = None
    channel_blob: Optional[bytes] = None
    raw: bytes = b""

    @property
    def type_name(self) -> str:
        return TYPE_NAMES.get(self.msg_type, f"UNKNOWN({self.msg_type})")

    @property
    def is_discovery(self) -> bool:
        return self.msg_type in DISCOVERY_TYPES

    @property
    def is_sealed(self) -> bool:
        return self.msg_type in SEALED_TYPES

    @property
    def is_channel(self) -> bool:
        return self.msg_type in CHANNEL_TYPES


def build_discovery(
    msg_type: int,
    public_key: bytes,
    *,
    body: bytes = b"",
    timestamp: float | None = None,
) -> bytes:
    """Construit une trame BEACON/PRESENCE en clair."""
    if msg_type not in DISCOVERY_TYPES:
        raise ValueError("build_discovery attend BEACON ou PRESENCE")
    if len(public_key) != PUB_LEN:
        raise ValueError("public_key doit faire 32 octets")
    if len(body) > 0xFFFF:
        raise ValueError("body trop long")
    node_id = node_id_from_pub(public_key).encode("ascii")
    ts = int(timestamp if timestamp is not None else time.time())
    return (
        MAGIC
        + bytes([msg_type])
        + node_id
        + public_key
        + struct.pack("!Q", ts & 0xFFFFFFFFFFFFFFFF)
        + struct.pack("!H", len(body))
        + body
    )


def build_sealed(msg_type: int, sender_pub: bytes, sealed_blob: bytes) -> bytes:
    """Construit une trame MSG/VOICE : en-tête clair + blob scellé."""
    if msg_type not in SEALED_TYPES:
        raise ValueError("build_sealed attend MSG ou VOICE")
    if len(sender_pub) != PUB_LEN:
        raise ValueError("sender_pub doit faire 32 octets")
    return MAGIC + bytes([msg_type]) + sender_pub + sealed_blob


def build_channel(channel_id: bytes, channel_blob: bytes) -> bytes:
    """Construit une trame CHANNEL_MSG=5."""
    if len(channel_id) != CHANNEL_ID_LEN:
        raise ValueError("channel_id doit faire 16 octets")
    return MAGIC + bytes([CHANNEL_MSG]) + channel_id + channel_blob


def parse_frame(data: bytes) -> Frame:
    """Parse une trame AirNet (découverte, scellée ou canal)."""
    if len(data) < 5:
        raise ValueError("trame trop courte")
    if data[:4] != MAGIC:
        raise ValueError("magic AIR1 manquant")
    msg_type = data[4]

    if msg_type in DISCOVERY_TYPES:
        if len(data) < HEADER_DISCOVERY:
            raise ValueError("trame découverte trop courte")
        node_id = data[5 : 5 + NODE_ID_LEN].decode("ascii")
        pub = data[5 + NODE_ID_LEN : 5 + NODE_ID_LEN + PUB_LEN]
        ts_off = 5 + NODE_ID_LEN + PUB_LEN
        (ts,) = struct.unpack("!Q", data[ts_off : ts_off + 8])
        (blen,) = struct.unpack("!H", data[ts_off + 8 : ts_off + 10])
        body = data[ts_off + 10 : ts_off + 10 + blen]
        expected = node_id_from_pub(pub)
        if node_id != expected:
            raise ValueError("node_id ne correspond pas à la clé publique")
        return Frame(
            msg_type=msg_type,
            sender_pub=pub,
            node_id=node_id,
            timestamp=float(ts),
            body=body,
            raw=data,
        )

    if msg_type in SEALED_TYPES:
        if len(data) < 5 + PUB_LEN + 1:
            raise ValueError("trame scellée trop courte")
        sender_pub = data[5 : 5 + PUB_LEN]
        sealed = data[5 + PUB_LEN :]
        return Frame(
            msg_type=msg_type,
            sender_pub=sender_pub,
            node_id=node_id_from_pub(sender_pub),
            sealed_blob=sealed,
            raw=data,
        )

    if msg_type == CHANNEL_MSG:
        if len(data) < 5 + CHANNEL_ID_LEN + 1:
            raise ValueError("trame canal trop courte")
        channel_id = data[5 : 5 + CHANNEL_ID_LEN]
        channel_blob = data[5 + CHANNEL_ID_LEN :]
        return Frame(
            msg_type=msg_type,
            channel_id=channel_id,
            channel_blob=channel_blob,
            raw=data,
        )

    raise ValueError(f"type de message inconnu: {msg_type}")
