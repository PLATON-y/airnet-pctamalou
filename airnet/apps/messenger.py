"""CLI messagerie AirNet — confiance directionnelle + canaux PSK.

Default DENY : on n'ouvre MSG/VOICE que si ``is_accepted(sender)``.
Envoi pairwise : destinataire doit être un contact accepté (ou utiliser --channel).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from airnet.crypto.channel import ChannelStore, default_channels_dir
from airnet.crypto.keys import generate_or_load_identity
from airnet.identity import AUTHOR, NAME, VERSION
from airnet.mesh.setup import setup_ibss_batman
from airnet.transport.framing import BEACON, CHANNEL_MSG, MSG, PRESENCE, VOICE, node_id_from_pub
from airnet.transport.udp import DEFAULT_PORT, UdpTransport, UntrustedSender
from airnet.trust.contacts import TrustStore, default_trust_dir

DEFAULT_QUEUE = Path("pending_messages.json")


def load_pending(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_pending(path: Path, messages: dict) -> None:
    path.write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="airnet-msg",
        description=f"{NAME} — messagerie scellée (trust + canaux)",
    )
    p.add_argument("--keys-dir", default=None)
    p.add_argument("--trust-dir", default=None)
    p.add_argument("--channels-dir", default=None)
    p.add_argument("--bind", default="0.0.0.0")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--no-mesh", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--iface", default=None)
    p.add_argument("--ip", default=None)
    p.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    p.add_argument("--gui", action="store_true", help="Tente PyQt5 si disponible")
    p.add_argument(
        "--listen",
        type=float,
        default=5.0,
        help="Secondes d'écoute initiale pour découvrir les pairs",
    )
    p.add_argument("--to", default=None, help="node_id destinataire (mode one-shot)")
    p.add_argument("--message", "-m", default=None, help="Message one-shot")
    p.add_argument("--peer-addr", default=None, help="IP du pair (défaut broadcast subnet)")
    p.add_argument("--channel", "-c", default=None, help="Envoyer via canal PSK (nom)")
    p.add_argument(
        "--accept",
        default=None,
        metavar="PUB_HEX",
        help="Accepter un pair (clé publique hex) puis quitter",
    )
    return p


def _try_gui() -> bool:
    try:
        import PyQt5  # noqa: F401

        return True
    except ImportError:
        return False


def _handle_incoming(
    transport: UdpTransport,
    frame,
    my_id: str,
    peers: dict,
    addr: tuple,
) -> None:
    if frame.msg_type in (BEACON, PRESENCE) and frame.node_id != my_id:
        peers[frame.node_id] = {
            "pub": frame.sender_pub,
            "addr": addr[0],
            "port": addr[1],
            "last": time.time(),
        }
        return
    if frame.msg_type in (MSG, VOICE) and frame.node_id != my_id:
        try:
            plain = transport.open_sealed_trusted(frame)
            text = plain.decode("utf-8", errors="replace")
            kind = "VOICE" if frame.msg_type == VOICE else "MSG"
            print(f"\n[{kind} {frame.node_id}] {text if kind == 'MSG' else f'({len(plain)} octets)'}")
        except UntrustedSender:
            print(f"\n[ignored untrusted] {frame.node_id} — accepte-le avec airnet-trust accept")
        except ValueError:
            pass
        return
    if frame.msg_type == CHANNEL_MSG:
        try:
            plain, cname = transport.open_channel_frame(frame)
            text = plain.decode("utf-8", errors="replace")
            print(f"\n[channel:{cname}] {text}")
        except ValueError:
            # secret inconnu → ignorer
            pass


def run_cli(
    transport: UdpTransport,
    identity,
    my_id: str,
    peers: dict[str, dict],
    queue_path: Path,
    trust: TrustStore,
    channels: ChannelStore,
    *,
    one_shot_to: str | None = None,
    one_shot_msg: str | None = None,
    one_shot_channel: str | None = None,
    peer_addr: str | None = None,
) -> int:
    pending = load_pending(queue_path)

    def discover(seconds: float) -> None:
        deadline = time.time() + seconds
        transport.send_discovery(PRESENCE)
        while time.time() < deadline:
            got = transport.recv_frame(timeout=0.5)
            if got is None:
                continue
            frame, addr = got
            _handle_incoming(transport, frame, my_id, peers, addr)

    # one-shot channel
    if one_shot_channel and one_shot_msg:
        meta = channels.get(one_shot_channel)
        if meta is None:
            print(f"[!] Canal inconnu : {one_shot_channel}", file=sys.stderr)
            return 1
        addr = (peer_addr, transport.port) if peer_addr else None
        transport.send_channel(one_shot_msg.encode("utf-8"), channel_name=meta.name, addr=addr)
        print(f"[me -> channel:{meta.name}] {one_shot_msg}")
        return 0

    if one_shot_to and one_shot_msg:
        # destinataire doit être contact accepté
        accepted = {c.node_id: c for c in trust.list_accepted()}
        if one_shot_to not in accepted and one_shot_to not in peers:
            print(f"[!] Pair {one_shot_to} inconnu — écoute découverte…")
            discover(8.0)
        contact = accepted.get(one_shot_to)
        if contact is None:
            # peut-être découvert mais pas accepté
            if one_shot_to in peers:
                print(
                    f"[!] {one_shot_to} découvert mais NON accepté.\n"
                    "    Confiance directionnelle : accepte-le d'abord :\n"
                    f"      airnet-trust accept --pub {peers[one_shot_to]['pub'].hex()}\n"
                    "    Ou utilise un canal : --channel NOM",
                    file=sys.stderr,
                )
                return 1
            pending.setdefault(one_shot_to, []).append(one_shot_msg)
            save_pending(queue_path, pending)
            print(f"[queue] Message mis en file pour {one_shot_to}")
            return 0
        pub = contact.public_bytes
        info = peers.get(one_shot_to, {})
        dest = (peer_addr or info.get("addr", "255.255.255.255"), info.get("port", transport.port))
        if dest[0] in ("0.0.0.0",) and peer_addr:
            dest = (peer_addr, transport.port)
        transport.send_sealed(
            one_shot_msg.encode("utf-8"),
            pub,
            msg_type=MSG,
            addr=dest,
        )
        print(f"[me -> {one_shot_to}] {one_shot_msg}")
        print("    (Il ne lira ce message que s'il t'a aussi accepté.)")
        return 0

    print("Commandes : list | accept <pub_hex> | send <node_id> <texte> |")
    print("            channel <nom> <texte> | listen [s] | quit")
    print("Confiance : tu ne lis que les pairs acceptés (default DENY).")
    while True:
        try:
            line = input("airnet-msg> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("quit", "exit", "q"):
            break
        if line == "list":
            print("--- Contacts acceptés ---")
            acc = trust.list_accepted()
            if not acc:
                print("  (aucun — default DENY)")
            for c in acc:
                print(f"  [trusted] {c.node_id}  {c.display_name or ''}")
            print("--- Découverts ---")
            if not peers:
                print("  (aucun — 'listen 10')")
            for nid, info in peers.items():
                status = "trusted" if trust.is_accepted(info["pub"]) else "unknown"
                print(f"  [{status}] {nid}  {info['addr']}:{info.get('port', transport.port)}")
            print("--- Canaux ---")
            for m in channels.list_channels():
                print(f"  [channel] {m.name}  id={m.channel_id[:16]}…")
            continue
        if line.startswith("accept "):
            parts = line.split(None, 1)
            if len(parts) < 2:
                print("usage: accept <pub_hex>")
                continue
            try:
                c = trust.accept_peer(parts[1].strip())
                print(f"[+] Accepté {c.node_id} — tu déchiffreras ses messages.")
            except ValueError as exc:
                print(f"[!] {exc}")
            continue
        if line.startswith("listen"):
            parts = line.split()
            secs = float(parts[1]) if len(parts) > 1 else 10.0
            print(f"[*] Écoute {secs}s…")
            discover(secs)
            print(f"[+] {len(peers)} pair(s) découverts")
            continue
        if line.startswith("channel "):
            parts = line.split(None, 2)
            if len(parts) < 3:
                print("usage: channel <nom> <texte>")
                continue
            _, cname, msg = parts
            meta = channels.get(cname)
            if meta is None:
                print(f"[!] Canal inconnu : {cname}")
                continue
            addr = (peer_addr, transport.port) if peer_addr else None
            transport.send_channel(msg.encode("utf-8"), channel_name=meta.name, addr=addr)
            print(f"[me -> channel:{meta.name}] {msg}")
            continue
        if line.startswith("send "):
            parts = line.split(None, 2)
            if len(parts) < 3:
                print("usage: send <node_id> <texte>")
                continue
            _, target, msg = parts
            accepted_map = {c.node_id: c for c in trust.list_accepted()}
            if target not in accepted_map:
                print(
                    f"[!] {target} n'est pas un contact accepté.\n"
                    "    Accepte d'abord (échange de clés OOB) :\n"
                    "      accept <pub_hex>   ou   airnet-trust accept --pub …\n"
                    "    Ou envoie sur un canal partagé : channel <nom> <texte>"
                )
                continue
            contact = accepted_map[target]
            if target not in peers:
                pending.setdefault(target, []).append(msg)
                save_pending(queue_path, pending)
                print(f"[queue] {target} hors ligne — message en file")
                continue
            info = peers[target]
            addr = (peer_addr or info["addr"], info.get("port", transport.port))
            transport.send_sealed(msg.encode("utf-8"), contact.public_bytes, msg_type=MSG, addr=addr)
            print(f"[me -> {target}] {msg}")
            print("    (Lecture côté pair seulement s'il t'a accepté — confiance à sens unique possible.)")
            if target in pending:
                for queued in pending.pop(target):
                    transport.send_sealed(
                        queued.encode("utf-8"),
                        contact.public_bytes,
                        msg_type=MSG,
                        addr=addr,
                    )
                    print(f"[me -> {target}] {queued} (from queue)")
                save_pending(queue_path, pending)
            continue
        print("Commande inconnue.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"🔥 {NAME} MESSENGER — {VERSION}")
    print(f"   Auteur : {AUTHOR}")
    print("   Politique : default DENY — accepte les pairs OOB avant de chatter.")

    if args.gui:
        if not _try_gui():
            print(
                "[!] PyQt5 indisponible. Installe l'extra : pip install 'airnet[gui]' "
                "ou utilise le mode CLI (défaut).",
                file=sys.stderr,
            )
        else:
            print(
                "[*] GUI demandée — squelette CLI prioritaire dans cette version ; "
                "lance sans --gui pour le mode fiable."
            )

    identity = generate_or_load_identity(args.keys_dir)
    my_id = node_id_from_pub(identity.public_bytes)
    trust = TrustStore(args.trust_dir or default_trust_dir(identity.keys_dir))
    channels = ChannelStore(args.channels_dir or default_channels_dir(identity.keys_dir))
    print(f"[+] node_id = {my_id}")
    print(f"[+] trust   = {trust.trust_dir} ({len(trust.list_accepted())} accepté(s))")

    if args.accept:
        c = trust.accept_peer(args.accept.strip())
        print(f"[+] Accepté : {c.node_id}")
        return 0

    if not args.no_mesh:
        try:
            setup_ibss_batman(
                iface=args.iface,
                ip_cidr=args.ip,
                dry_run=args.dry_run,
            )
        except Exception as exc:
            print(f"[!] mesh : {exc}", file=sys.stderr)
            if not args.dry_run:
                return 1

    bind_ip = "127.0.0.1" if args.dry_run and args.bind == "0.0.0.0" else args.bind
    transport = UdpTransport(
        bind_ip=bind_ip,
        port=args.port,
        identity=identity,
        broadcast=True,
        trust=trust,
        channels=channels,
    )
    peers: dict[str, dict] = {}
    try:
        if args.listen > 0 and not ((args.to and args.message) or (args.channel and args.message)):
            print(f"[*] Découverte initiale ({args.listen}s)…")
            deadline = time.time() + args.listen
            transport.send_discovery(PRESENCE)
            while time.time() < deadline:
                got = transport.recv_frame(timeout=0.5)
                if got is None:
                    continue
                frame, addr = got
                _handle_incoming(transport, frame, my_id, peers, addr)
            print(f"[+] {len(peers)} pair(s) découverts")

        return run_cli(
            transport,
            identity,
            my_id,
            peers,
            args.queue,
            trust,
            channels,
            one_shot_to=args.to,
            one_shot_msg=args.message,
            one_shot_channel=args.channel,
            peer_addr=args.peer_addr,
        )
    finally:
        transport.close()


if __name__ == "__main__":
    raise SystemExit(main())
