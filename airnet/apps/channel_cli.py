"""CLI canaux PSK AirNet — create / join / list / send."""

from __future__ import annotations

import argparse
import sys

from airnet.crypto.channel import ChannelStore, default_channels_dir
from airnet.crypto.keys import generate_or_load_identity
from airnet.identity import AUTHOR, NAME, VERSION
from airnet.transport.framing import node_id_from_pub
from airnet.transport.udp import DEFAULT_PORT, UdpTransport


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="airnet-channel",
        description=f"{NAME} — canaux à secret partagé (OOB, pair ou groupe)",
    )
    p.add_argument("--keys-dir", default=None)
    p.add_argument("--channels-dir", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    cre = sub.add_parser("create", help="Créer un canal (génère ou prend un secret)")
    cre.add_argument("--name", required=True)
    cre.add_argument(
        "--secret",
        default=None,
        help="Secret (passphrase ou hex 64). '-' = lire stdin. Défaut = aléatoire 32B.",
    )
    cre.add_argument("--type", choices=("pair", "group"), default="group")
    cre.add_argument(
        "--show-secret",
        action="store_true",
        help="Affiche le secret une fois (à échanger OOB — ne pas logger ailleurs)",
    )

    jo = sub.add_parser("join", help="Importer un canal (même nom+secret)")
    jo.add_argument("--name", required=True)
    jo.add_argument("--secret", required=True, help="Secret ou '-' pour stdin")
    jo.add_argument("--type", choices=("pair", "group"), default="group")

    sub.add_parser("list", help="Lister les canaux locaux")

    snd = sub.add_parser("send", help="Envoyer un CHANNEL_MSG")
    snd.add_argument("--channel", "-c", required=True, help="Nom ou id de canal")
    snd.add_argument("message", nargs="?", default=None)
    snd.add_argument("--bind", default="0.0.0.0")
    snd.add_argument("--port", type=int, default=DEFAULT_PORT)
    snd.add_argument("--peer-addr", default=None, help="IP unicast (défaut broadcast)")
    return p


def _secret_arg(value: str | None) -> str | bytes | None:
    if value is None:
        return None
    if value == "-":
        data = sys.stdin.buffer.read()
        text = data.decode("utf-8", errors="replace").strip()
        return text
    return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"🔑 {NAME} CHANNEL — {VERSION}")
    print(f"   Auteur : {AUTHOR}")

    identity = generate_or_load_identity(args.keys_dir)
    ch_dir = args.channels_dir or default_channels_dir(identity.keys_dir)
    store = ChannelStore(ch_dir)
    print(f"[+] channels_dir = {store.channels_dir}")

    if args.cmd == "create":
        secret = _secret_arg(args.secret)
        meta, raw = store.create(args.name, secret, channel_type=args.type)
        print(f"[+] Canal créé : {meta.name}  id={meta.channel_id}  type={meta.channel_type}")
        print("    Échange le secret hors bande (QR / USB / oral / Signal…).")
        print("    Ne jamais coller le secret dans un log ou un ticket.")
        if args.show_secret or args.secret is None:
            # afficher une fois pour OOB
            if len(raw) == 32 and (args.secret is None or (isinstance(args.secret, str) and len(args.secret) == 64)):
                print(f"    secret (hex, une fois) : {raw.hex()}")
            else:
                try:
                    print(f"    secret (utf-8) : {raw.decode('utf-8')}")
                except UnicodeDecodeError:
                    print(f"    secret (hex) : {raw.hex()}")
        return 0

    if args.cmd == "join":
        secret = _secret_arg(args.secret)
        if secret is None:
            print("[!] --secret requis", file=sys.stderr)
            return 2
        meta = store.join(args.name, secret, channel_type=args.type)
        print(f"[+] Canal rejoint : {meta.name}  id={meta.channel_id}")
        return 0

    if args.cmd == "list":
        chans = store.list_channels()
        if not chans:
            print("(aucun canal)")
            return 0
        for m in chans:
            print(f"  {m.name}  id={m.channel_id}  type={m.channel_type}")
        return 0

    if args.cmd == "send":
        msg = args.message
        if msg is None:
            msg = sys.stdin.read()
        if not msg:
            print("[!] message vide", file=sys.stderr)
            return 2
        meta = store.get(args.channel)
        if meta is None:
            print(f"[!] Canal inconnu : {args.channel}", file=sys.stderr)
            return 1
        my_id = node_id_from_pub(identity.public_bytes)
        bind_ip = args.bind
        transport = UdpTransport(
            bind_ip=bind_ip,
            port=args.port,
            identity=identity,
            broadcast=True,
            channels=store,
        )
        try:
            addr = (args.peer_addr, args.port) if args.peer_addr else None
            transport.send_channel(msg.encode("utf-8"), channel_name=meta.name, addr=addr)
            print(f"[me/{my_id} -> channel:{meta.name}] {msg}")
        finally:
            transport.close()
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
