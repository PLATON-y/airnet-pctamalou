"""CLI connecteur AirNet — rejoindre le mesh et découvrir les pairs (trusted/unknown)."""

from __future__ import annotations

import argparse
import sys
import time

from airnet.crypto.keys import generate_or_load_identity
from airnet.identity import AUTHOR, NAME, VERSION
from airnet.mesh.setup import setup_ibss_batman
from airnet.transport.framing import BEACON, PRESENCE, node_id_from_pub
from airnet.transport.udp import DEFAULT_PORT, UdpTransport
from airnet.trust.contacts import TrustStore, default_trust_dir


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="airnet-connect",
        description=f"{NAME} — découverte de nœuds (BEACON/PRESENCE)",
    )
    p.add_argument("--keys-dir", default=None)
    p.add_argument("--trust-dir", default=None)
    p.add_argument("--bind", default="0.0.0.0")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--iface", default=None)
    p.add_argument("--ip", default=None)
    p.add_argument("--no-mesh", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--timeout", type=float, default=30.0, help="Durée d'écoute (s)")
    p.add_argument("--stale", type=float, default=30.0, help="TTL nœud actif (s)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"🔥 {NAME} CONNECTOR — {VERSION}")
    print(f"   Auteur : {AUTHOR}")

    identity = generate_or_load_identity(args.keys_dir)
    my_id = node_id_from_pub(identity.public_bytes)
    trust = TrustStore(args.trust_dir or default_trust_dir(identity.keys_dir))
    print(f"[+] mon node_id = {my_id}")
    print(f"[+] trust       = {len(trust.list_accepted())} accepté(s)")

    if not args.no_mesh:
        try:
            result = setup_ibss_batman(
                iface=args.iface,
                ip_cidr=args.ip,
                dry_run=args.dry_run,
            )
            print(f"[+] mesh = {result['ip_cidr']} dry_run={result['dry_run']}")
        except Exception as exc:
            print(f"[!] Setup mesh : {exc}", file=sys.stderr)
            if not args.dry_run:
                return 1

    bind_ip = "127.0.0.1" if args.dry_run and args.bind == "0.0.0.0" else args.bind
    known: dict[str, dict] = {}
    transport = UdpTransport(
        bind_ip=bind_ip,
        port=args.port,
        identity=identity,
        broadcast=True,
        trust=trust,
    )
    transport.send_discovery(PRESENCE)
    print(f"[*] Écoute {args.timeout}s sur {bind_ip}:{args.port} …")
    print("    (BEACON/PRESENCE visibles même unknown — chat seulement après accept)")

    deadline = time.time() + args.timeout
    try:
        while time.time() < deadline:
            remaining = max(0.1, deadline - time.time())
            got = transport.recv_frame(timeout=min(1.0, remaining))
            if got is None:
                continue
            frame, addr = got
            if frame.msg_type not in (BEACON, PRESENCE):
                continue
            if frame.node_id == my_id:
                continue
            status = "trusted" if trust.is_accepted(frame.sender_pub) else "unknown"
            known[frame.node_id] = {
                "pub": frame.sender_pub.hex(),
                "last": time.time(),
                "addr": addr[0],
                "type": frame.type_name,
                "status": status,
            }
            active = {
                k: v
                for k, v in known.items()
                if time.time() - v["last"] < args.stale
            }
            print(
                f"🎯 [{status}] {frame.node_id} ({frame.type_name} @ {addr[0]}) "
                f"— actifs : {len(active)}"
            )
    except KeyboardInterrupt:
        print("\n[+] Écoute interrompue.")
    finally:
        transport.close()

    now = time.time()
    active = {k: v for k, v in known.items() if now - v["last"] < args.stale}
    if not active:
        print("Aucun nœud détecté. Vérifie portée / lance airnet-node près de toi.")
        return 0

    print("\n=== Nœuds actifs ===")
    for nid, info in sorted(active.items()):
        print(
            f"  [{info['status']}] {nid}  addr={info['addr']}  "
            f"last_type={info['type']}  pub={info['pub'][:16]}…"
        )
        if info["status"] == "unknown":
            print(f"           → airnet-trust accept --pub {info['pub']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
