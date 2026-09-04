"""Canaux PSK (clé partagée OOB) — pair ou groupe.

Création : nom + secret (passphrase ou 32 octets aléatoires) échangés hors bande
(QR, USB, oral, Signal, etc. — QR non implémenté ici).

Dérivation : HKDF-SHA256(secret, salt=b"AirNet-channel-v1", info=channel_id).
AEAD : ChaCha20-Poly1305 (pas d'ECDH). Membership = connaître le secret.

Métadonnées locales : id, name, type — secret en fichier mode 0o600, jamais loggé
en clair.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

CHANNEL_BLOB_VERSION = 0x01
NONCE_SIZE = 12
TAG_SIZE = 16
CHANNEL_ID_LEN = 16
HKDF_SALT = b"AirNet-channel-v1"

ChannelType = Literal["pair", "group"]


def default_channels_dir(keys_dir: Path | str | None = None) -> Path:
    env = os.environ.get("AIRNET_CHANNELS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    if keys_dir is not None:
        kd = Path(keys_dir).expanduser().resolve()
        if kd.name == "keys":
            return kd.parent / "channels"
        return kd / "channels"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "airnet" / "channels"
    home_cfg = Path.home() / ".config" / "airnet" / "channels"
    try:
        home_cfg.parent.mkdir(parents=True, exist_ok=True)
        return home_cfg
    except OSError:
        return (Path.cwd() / "data" / "channels").resolve()


def _ensure_secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _write_secret(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    return s[:48] or "channel"


def channel_id_from_name_secret(name: str, secret: bytes) -> bytes:
    """Identifiant 16 octets déterministe : SHA-256(name || 0x00 || secret)[:16].

    Tous les membres qui partagent le même nom+secret obtiennent le même id.
    """
    h = hashlib.sha256()
    h.update(name.encode("utf-8"))
    h.update(b"\x00")
    h.update(secret)
    return h.digest()[:CHANNEL_ID_LEN]


def derive_channel_key(secret: bytes, channel_id: bytes) -> bytes:
    if len(channel_id) != CHANNEL_ID_LEN:
        raise ValueError("channel_id doit faire 16 octets")
    if not secret:
        raise ValueError("secret vide")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=HKDF_SALT,
        info=channel_id,
    ).derive(secret)


def normalize_secret(secret: str | bytes) -> bytes:
    if isinstance(secret, bytes):
        return secret
    s = secret.strip()
    # hex 64 → 32 raw bytes
    if len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s):
        return bytes.fromhex(s)
    return s.encode("utf-8")


@dataclass
class ChannelMeta:
    channel_id: str  # hex 32
    name: str
    channel_type: ChannelType
    created_at: float

    @property
    def id_bytes(self) -> bytes:
        return bytes.fromhex(self.channel_id)

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "type": self.channel_type,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelMeta":
        return cls(
            channel_id=str(data["channel_id"]).lower(),
            name=str(data["name"]),
            channel_type=data.get("type", "group"),  # type: ignore[arg-type]
            created_at=float(data.get("created_at", 0)),
        )


def seal_channel(plaintext: bytes, key: bytes, channel_id: bytes) -> bytes:
    """Chiffre pour un canal PSK. Retourne ``version | nonce | ct||tag``."""
    if len(key) != 32:
        raise ValueError("clé canal : 32 octets")
    if len(channel_id) != CHANNEL_ID_LEN:
        raise ValueError("channel_id : 16 octets")
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("plaintext doit être bytes")
    nonce = os.urandom(NONCE_SIZE)
    aead = ChaCha20Poly1305(key)
    aad = bytes([CHANNEL_BLOB_VERSION]) + channel_id
    ct = aead.encrypt(nonce, bytes(plaintext), aad)
    return bytes([CHANNEL_BLOB_VERSION]) + nonce + ct


def open_channel(blob: bytes, key: bytes, channel_id: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("clé canal : 32 octets")
    if len(channel_id) != CHANNEL_ID_LEN:
        raise ValueError("channel_id : 16 octets")
    if len(blob) < 1 + NONCE_SIZE + TAG_SIZE:
        raise ValueError("blob canal trop court")
    if blob[0] != CHANNEL_BLOB_VERSION:
        raise ValueError(f"version canal non supportée: {blob[0]}")
    nonce = bytes(blob[1 : 1 + NONCE_SIZE])
    ct = bytes(blob[1 + NONCE_SIZE :])
    aead = ChaCha20Poly1305(key)
    aad = bytes([CHANNEL_BLOB_VERSION]) + channel_id
    try:
        return aead.decrypt(nonce, ct, aad)
    except Exception as exc:
        raise ValueError("échec d'ouverture canal (auth/intégrité)") from exc


class ChannelStore:
    """Métadonnées + secrets locaux (secret jamais dans les logs)."""

    def __init__(self, channels_dir: Path | str | None = None, *, keys_dir: Path | str | None = None) -> None:
        self.channels_dir = (
            Path(channels_dir).expanduser().resolve()
            if channels_dir
            else default_channels_dir(keys_dir)
        )
        _ensure_secure_dir(self.channels_dir)

    def _meta_path(self, channel_id_hex: str) -> Path:
        return self.channels_dir / f"{channel_id_hex}.json"

    def _secret_path(self, channel_id_hex: str) -> Path:
        return self.channels_dir / f"{channel_id_hex}.secret"

    def create(
        self,
        name: str,
        secret: str | bytes | None = None,
        *,
        channel_type: ChannelType = "group",
    ) -> tuple[ChannelMeta, bytes]:
        """Crée un canal. Si ``secret`` est None, génère 32 octets aléatoires."""
        if not name or not name.strip():
            raise ValueError("nom de canal requis")
        if secret is None:
            raw_secret = secrets.token_bytes(32)
        else:
            raw_secret = normalize_secret(secret)
        cid = channel_id_from_name_secret(name.strip(), raw_secret)
        cid_hex = cid.hex()
        meta = ChannelMeta(
            channel_id=cid_hex,
            name=name.strip(),
            channel_type=channel_type,
            created_at=time.time(),
        )
        self._persist(meta, raw_secret)
        return meta, raw_secret

    def join(
        self,
        name: str,
        secret: str | bytes,
        *,
        channel_type: ChannelType = "group",
    ) -> ChannelMeta:
        """Importe un canal existant (même nom+secret → même id)."""
        raw_secret = normalize_secret(secret)
        cid = channel_id_from_name_secret(name.strip(), raw_secret)
        cid_hex = cid.hex()
        meta = ChannelMeta(
            channel_id=cid_hex,
            name=name.strip(),
            channel_type=channel_type,
            created_at=time.time(),
        )
        self._persist(meta, raw_secret)
        return meta

    def _persist(self, meta: ChannelMeta, secret: bytes) -> None:
        _ensure_secure_dir(self.channels_dir)
        self._meta_path(meta.channel_id).write_text(
            json.dumps(meta.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(self._meta_path(meta.channel_id), 0o600)
        except OSError:
            pass
        _write_secret(self._secret_path(meta.channel_id), secret)

    def list_channels(self) -> list[ChannelMeta]:
        out: list[ChannelMeta] = []
        if not self.channels_dir.is_dir():
            return out
        for path in sorted(self.channels_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                out.append(ChannelMeta.from_dict(data))
            except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
                continue
        return out

    def get(self, name_or_id: str) -> Optional[ChannelMeta]:
        needle = name_or_id.strip().lower()
        for meta in self.list_channels():
            if meta.channel_id == needle or meta.name.lower() == needle:
                return meta
            if meta.channel_id.startswith(needle) and len(needle) >= 8:
                return meta
        return None

    def load_secret(self, meta: ChannelMeta) -> bytes:
        path = self._secret_path(meta.channel_id)
        if not path.is_file():
            raise FileNotFoundError(f"secret canal manquant : {meta.name}")
        return path.read_bytes()

    def get_key(self, meta: ChannelMeta) -> bytes:
        secret = self.load_secret(meta)
        return derive_channel_key(secret, meta.id_bytes)

    def encrypt(self, meta: ChannelMeta, plaintext: bytes) -> bytes:
        key = self.get_key(meta)
        return seal_channel(plaintext, key, meta.id_bytes)

    def decrypt(self, meta: ChannelMeta, blob: bytes) -> bytes:
        key = self.get_key(meta)
        return open_channel(blob, key, meta.id_bytes)

    def decrypt_by_id(self, channel_id: bytes, blob: bytes) -> bytes:
        cid_hex = channel_id.hex()
        meta = self.get(cid_hex)
        if meta is None:
            raise ValueError("canal inconnu localement")
        return self.decrypt(meta, blob)
