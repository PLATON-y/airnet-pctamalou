"""Identités nœud X25519 persistées (répertoire configurable, modes 0o700/0o600)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

DEFAULT_KEYS_SUBDIR = Path("airnet") / "keys"
PRIVATE_FILENAME = "identity.x25519"
PUBLIC_FILENAME = "identity.x25519.pub"


def default_keys_dir() -> Path:
    """Répertoire des clés : AIRNET_KEYS_DIR, sinon ~/.config/airnet/keys, sinon ./data/keys."""
    env = os.environ.get("AIRNET_KEYS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / DEFAULT_KEYS_SUBDIR
    home_cfg = Path.home() / ".config" / DEFAULT_KEYS_SUBDIR
    # Prefer XDG-style home config; fall back to ./data/keys if home is unusable
    try:
        home_cfg.parent.mkdir(parents=True, exist_ok=True)
        return home_cfg
    except OSError:
        return (Path.cwd() / "data" / "keys").resolve()


@dataclass
class Identity:
    """Paire de clés X25519 d'un nœud AirNet."""

    private_key: X25519PrivateKey
    public_key: X25519PublicKey
    keys_dir: Path

    @property
    def public_bytes(self) -> bytes:
        return self.public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

    @property
    def private_bytes(self) -> bytes:
        return self.private_key.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )


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


def generate_or_load_identity(keys_dir: Path | str | None = None) -> Identity:
    """Génère ou charge l'identité X25519 du nœud local.

    Parameters
    ----------
    keys_dir :
        Répertoire de persistance. Défaut via ``default_keys_dir()``.
    """
    directory = Path(keys_dir).expanduser().resolve() if keys_dir else default_keys_dir()
    _ensure_secure_dir(directory)

    priv_path = directory / PRIVATE_FILENAME
    pub_path = directory / PUBLIC_FILENAME

    if priv_path.is_file():
        raw = priv_path.read_bytes()
        if len(raw) != 32:
            raise ValueError(f"Clé privée invalide ({len(raw)} octets) dans {priv_path}")
        private_key = X25519PrivateKey.from_private_bytes(raw)
        public_key = private_key.public_key()
        # Réécrire la publique si absente / désynchronisée
        expected_pub = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        if not pub_path.is_file() or pub_path.read_bytes() != expected_pub:
            _write_secret(pub_path, expected_pub)
        return Identity(private_key=private_key, public_key=public_key, keys_dir=directory)

    private_key = X25519PrivateKey.generate()
    public_key = private_key.public_key()
    _write_secret(
        priv_path,
        private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
    )
    _write_secret(
        pub_path,
        public_key.public_bytes(Encoding.Raw, PublicFormat.Raw),
    )
    return Identity(private_key=private_key, public_key=public_key, keys_dir=directory)


def public_key_from_bytes(data: bytes) -> X25519PublicKey:
    if len(data) != 32:
        raise ValueError("Clé publique X25519 attendue sur 32 octets")
    return X25519PublicKey.from_public_bytes(data)
