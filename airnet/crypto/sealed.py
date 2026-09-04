"""Boîte scellée : ECDH X25519 + HKDF-SHA256 + ChaCha20-Poly1305.

Format blob v1
--------------
    version (1 octet = 0x01)
    nonce   (12 octets)
    ciphertext || tag Poly1305 (len(plaintext) + 16)

Pas de CBC, pas de XOR sinusoïdal, pas de clé en dur.
"""

from __future__ import annotations

import os
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from airnet.crypto.keys import Identity, generate_or_load_identity, public_key_from_bytes

BLOB_VERSION = 0x01
NONCE_SIZE = 12
TAG_SIZE = 16
HKDF_INFO = b"airnet-seal-v1"
HKDF_SALT = b"AirNet-PCTamalou-Phase1"


def _derive_aead_key(
    private_key: X25519PrivateKey,
    peer_public: bytes,
) -> bytes:
    shared = private_key.exchange(public_key_from_bytes(peer_public))
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=HKDF_SALT,
        info=HKDF_INFO,
    ).derive(shared)


def _resolve_identity(identity: Optional[Identity]) -> Identity:
    if identity is not None:
        return identity
    return generate_or_load_identity()


def seal(
    plaintext: bytes,
    recipient_public: bytes,
    identity: Optional[Identity] = None,
) -> bytes:
    """Chiffre ``plaintext`` pour ``recipient_public`` (X25519 raw 32 octets).

    Utilise la clé privée de l'identité locale (chargée ou fournie).
    """
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("plaintext doit être bytes")
    if len(recipient_public) != 32:
        raise ValueError("recipient_public doit faire 32 octets")

    ident = _resolve_identity(identity)
    key = _derive_aead_key(ident.private_key, recipient_public)
    nonce = os.urandom(NONCE_SIZE)
    aead = ChaCha20Poly1305(key)
    # AAD = version + pub destinataire pour lier le blob au contexte
    aad = bytes([BLOB_VERSION]) + recipient_public
    ciphertext = aead.encrypt(nonce, bytes(plaintext), aad)
    return bytes([BLOB_VERSION]) + nonce + ciphertext


def open(
    blob: bytes,
    sender_public: bytes,
    identity: Optional[Identity] = None,
) -> bytes:
    """Déchiffre un blob produit par ``seal``, authentifié via ``sender_public``."""
    if not isinstance(blob, (bytes, bytearray)):
        raise TypeError("blob doit être bytes")
    if len(sender_public) != 32:
        raise ValueError("sender_public doit faire 32 octets")
    if len(blob) < 1 + NONCE_SIZE + TAG_SIZE:
        raise ValueError("blob trop court")

    version = blob[0]
    if version != BLOB_VERSION:
        raise ValueError(f"version de blob non supportée: {version}")

    nonce = bytes(blob[1 : 1 + NONCE_SIZE])
    ciphertext = bytes(blob[1 + NONCE_SIZE :])

    ident = _resolve_identity(identity)
    key = _derive_aead_key(ident.private_key, sender_public)
    aead = ChaCha20Poly1305(key)
    # Côté destinataire, AAD lie à *notre* clé publique (celle du recipient au seal)
    aad = bytes([BLOB_VERSION]) + ident.public_bytes
    try:
        return aead.decrypt(nonce, ciphertext, aad)
    except Exception as exc:  # InvalidTag etc.
        raise ValueError("échec d'ouverture du blob (auth/intégrité)") from exc
