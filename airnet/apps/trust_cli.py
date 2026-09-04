"""CLI confiance AirNet — accept / revoke / list (default DENY)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from airnet.crypto.keys import generate_or_load_identity
from airnet.identity import AUTHOR, NAME, VERSION
from airnet.transport.framing import node_id_from_pub
from airnet.trust.contacts import TrustStore, default_trust_dir


def _read_pub(args: argparse.Namespace) -> bytes:
    if args.file:
        raw = Path(args.file).read_bytes().strip()
        # fichier .pub raw 32B ou hex texte
        if len(raw) == 32:
            return raw
        text = raw.decode("utf-8", errors="replace").strip()
        return bytes.fromhex(text)
    if args.pub:
        return bytes.fromhex(args.pub.strip())
    raise SystemExit("fournis --pub HEX ou --file chemin")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="airnet-trust",
        description=f"{NAME} — confiance (acceptation explicite, default DENY)",
    )
    p.add_argument("--keys-dir", default=None)
    p.add_argument("--trust-dir", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    acc = sub.add_parser("accept", help="Accepter un pair (déchiffrer ses messages)")
    acc.add_argument("--pub", default=None, help="Clé publique hex (64)")
    acc.add_argument("--file", default=None, help="Fichier .pub (raw 32B ou hex)")
    acc.add_argument("--name", default=None, help="Nom d'affichage optionnel")

    rev = sub.add_parser("revoke", help="Révoquer un pair")
    rev.add_argument("--pub", default=None)
    rev.add_argument("--file", default=None)
    rev.add_argument("--node-id", default=None, help="node_id 16 hex")

    sub.add_parser("list", help="Lister les pairs acceptés")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"🔐 {NAME} TRUST — {VERSION}")
    print(f"   Auteur : {AUTHOR}")

    identity = generate_or_load_identity(args.keys_dir)
    my_id = node_id_from_pub(identity.public_bytes)
    trust_dir = args.trust_dir or default_trust_dir(identity.keys_dir)
    store = TrustStore(trust_dir)
    print(f"[+] mon node_id = {my_id}")
    print(f"[+] trust_dir   = {store.trust_dir}")

    if args.cmd == "accept":
        pub = _read_pub(args)
        c = store.accept_peer(pub, display_name=args.name)
        print(f"[+] Accepté : {c.node_id}  pub={c.public_key[:16]}…")
        print("    → Tu déchiffreras ses MSG/VOICE.")
        print("    → Lui ne lira les tiens que s'il t'accepte aussi (confiance directionnelle).")
        return 0

    if args.cmd == "revoke":
        target: str | bytes
        if args.node_id:
            target = args.node_id
        else:
            target = _read_pub(args)
        if store.revoke_peer(target):
            print("[+] Pair révoqué — ses messages seront ignorés.")
            return 0
        print("[!] Pair introuvable.", file=sys.stderr)
        return 1

    if args.cmd == "list":
        accepted = store.list_accepted()
        if not accepted:
            print("(aucun pair accepté — default DENY)")
            return 0
        for c in accepted:
            name = f"  ({c.display_name})" if c.display_name else ""
            print(f"  {c.node_id}{name}  pub={c.public_key}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
