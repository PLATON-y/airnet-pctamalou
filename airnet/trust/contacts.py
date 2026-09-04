"""Store de confiance persistant — default DENY sauf acceptation explicite.

Chaque pair : node_id, public_key (hex 64), accepted (bool), display_name?, added_at.

``accepted=True`` ⇒ on DÉCHIFFRE les MSG/VOICE de ce pair.
Sans acceptation ⇒ ignore silencieuse (ou log « ignored untrusted »).
Les BEACON/PRESENCE restent visibles comme « unknown peer ».
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CONTACTS_FILENAME = "contacts.json"


def _node_id_from_pub(public_key: bytes) -> str:
    if len(public_key) != 32:
        raise ValueError("clé publique : 32 octets attendus")
    return hashlib.sha256(public_key).hexdigest()[:16]


def default_trust_dir(keys_dir: Path | str | None = None) -> Path:
    """Répertoire trust : AIRNET_TRUST_DIR, sinon sibling de keys, sinon ~/.config/airnet/trust."""
    env = os.environ.get("AIRNET_TRUST_DIR")
    if env:
        return Path(env).expanduser().resolve()
    if keys_dir is not None:
        kd = Path(keys_dir).expanduser().resolve()
        # keys_dir = .../airnet/keys → trust = .../airnet/trust
        if kd.name == "keys":
            return kd.parent / "trust"
        return kd / "trust"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "airnet" / "trust"
    home_cfg = Path.home() / ".config" / "airnet" / "trust"
    try:
        home_cfg.parent.mkdir(parents=True, exist_ok=True)
        return home_cfg
    except OSError:
        return (Path.cwd() / "data" / "trust").resolve()


def _ensure_secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


@dataclass
class Contact:
    node_id: str
    public_key: str  # hex 64
    accepted: bool
    added_at: float
    display_name: Optional[str] = None

    @property
    def public_bytes(self) -> bytes:
        return bytes.fromhex(self.public_key)

    def to_dict(self) -> dict:
        d = {
            "node_id": self.node_id,
            "public_key": self.public_key,
            "accepted": self.accepted,
            "added_at": self.added_at,
        }
        if self.display_name:
            d["display_name"] = self.display_name
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Contact":
        return cls(
            node_id=str(data["node_id"]),
            public_key=str(data["public_key"]).lower(),
            accepted=bool(data.get("accepted", False)),
            added_at=float(data.get("added_at", 0)),
            display_name=data.get("display_name"),
        )


class TrustStore:
    """Contacts persistés en JSON (mode fichier 0o600)."""

    def __init__(self, trust_dir: Path | str | None = None, *, keys_dir: Path | str | None = None) -> None:
        self.trust_dir = Path(trust_dir).expanduser().resolve() if trust_dir else default_trust_dir(keys_dir)
        _ensure_secure_dir(self.trust_dir)
        self.path = self.trust_dir / CONTACTS_FILENAME
        self._contacts: dict[str, Contact] = {}  # key = public_key hex
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            self._contacts = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._contacts = {}
            return
        peers = raw.get("peers", raw) if isinstance(raw, dict) else []
        if isinstance(peers, dict):
            peers = list(peers.values())
        self._contacts = {}
        for item in peers:
            try:
                c = Contact.from_dict(item)
                self._contacts[c.public_key] = c
            except (KeyError, ValueError, TypeError):
                continue

    def _save(self) -> None:
        _ensure_secure_dir(self.trust_dir)
        payload = {
            "version": 1,
            "peers": [c.to_dict() for c in sorted(self._contacts.values(), key=lambda x: x.added_at)],
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _resolve_pub(self, pub_or_node_id: str | bytes) -> bytes:
        """Résout une clé publique 32B depuis hex, bytes, ou node_id déjà connu."""
        if isinstance(pub_or_node_id, (bytes, bytearray)):
            raw = bytes(pub_or_node_id)
            if len(raw) != 32:
                raise ValueError("clé publique : 32 octets attendus")
            return raw
        s = pub_or_node_id.strip().lower()
        if len(s) == 64 and all(c in "0123456789abcdef" for c in s):
            return bytes.fromhex(s)
        # node_id (16 hex) — chercher dans les contacts
        for c in self._contacts.values():
            if c.node_id == s:
                return c.public_bytes
        raise ValueError(
            f"introuvable : fournis une clé publique hex (64) ou un node_id déjà en contacts ({s!r})"
        )

    def accept_peer(
        self,
        pub_or_node_id: str | bytes,
        *,
        display_name: str | None = None,
    ) -> Contact:
        """Accepte un pair : on déchiffrera ses MSG/VOICE. Persiste le contact."""
        pub = self._resolve_pub(pub_or_node_id)
        # Si on n'avait que node_id et pas la pub, _resolve_pub a trouvé dans contacts ;
        # pour une nouvelle pub hex, on crée.
        hex_pub = pub.hex()
        nid = _node_id_from_pub(pub)
        existing = self._contacts.get(hex_pub)
        contact = Contact(
            node_id=nid,
            public_key=hex_pub,
            accepted=True,
            added_at=existing.added_at if existing else time.time(),
            display_name=display_name
            if display_name is not None
            else (existing.display_name if existing else None),
        )
        self._contacts[hex_pub] = contact
        self._save()
        return contact

    def revoke_peer(self, pub_or_node_id: str | bytes) -> bool:
        """Révoque l'acceptation (ou retire le contact). Retourne True si trouvé."""
        try:
            pub = self._resolve_pub(pub_or_node_id)
        except ValueError:
            return False
        hex_pub = pub.hex()
        if hex_pub not in self._contacts:
            # essayer par node_id string direct
            s = pub_or_node_id.strip().lower() if isinstance(pub_or_node_id, str) else ""
            for k, c in list(self._contacts.items()):
                if c.node_id == s:
                    del self._contacts[k]
                    self._save()
                    return True
            return False
        del self._contacts[hex_pub]
        self._save()
        return True

    def list_accepted(self) -> list[Contact]:
        return sorted(
            [c for c in self._contacts.values() if c.accepted],
            key=lambda c: c.added_at,
        )

    def list_all(self) -> list[Contact]:
        return sorted(self._contacts.values(), key=lambda c: c.added_at)

    def get_by_pub(self, sender_pub: bytes | str) -> Optional[Contact]:
        if isinstance(sender_pub, str):
            hex_pub = sender_pub.strip().lower()
        else:
            if len(sender_pub) != 32:
                return None
            hex_pub = sender_pub.hex()
        return self._contacts.get(hex_pub)

    def is_accepted(self, sender_pub: bytes | str) -> bool:
        """True ssi le pair est accepté → on peut ouvrir ses messages."""
        c = self.get_by_pub(sender_pub)
        return bool(c and c.accepted)

    def has_contact(self, pub: bytes | str) -> bool:
        return self.get_by_pub(pub) is not None
