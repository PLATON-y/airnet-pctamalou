"""CLI nœud AirNet — setup mesh, beacons périodiques.

Le relais L2 est géré par batman-adv ; ce processus annonce seulement
sa présence (BEACON) et reste actif.
"""

from __future__ import annotations

import argparse
import sys
import time

from airnet.crypto.keys import generate_or_load_identity
from airnet.identity import AUTHOR, NAME, VERSION
from airnet.mesh.setup import setup_ibss_batman
from airnet.transport.framing import BEACON, node_id_from_pub
from airnet.transport.udp import DEFAULT_PORT, UdpTransport


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="airnet-node",
        description=f"{NAME} — nœud mesh (beacons UDP)",
    )
    p.add_argument("--keys-dir", default=None, help="Répertoire des clés X25519")
    p.add_argument("--bind", default="0.0.0.0", help="IP de bind UDP")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--iface", default=None, help="Interface Wi-Fi (auto si omis)")
    p.add_argument("--ip", default=None, help="CIDR bat0 (ex. 10.13.37.10/24)")
    p.add_argument("--no-mesh", action="store_true", help="Ne pas configurer IBSS/batman")
    p.add_argument("--dry-run", action="store_true", help="Plan mesh sans commandes root")
    p.add_argument("--interval", type=float, default=10.0, help="Intervalle beacon (s)")
    p.add_argument(
        "--txpower",
        type=int,
        default=None,
        help="txpower dBm optionnel (≤ 20, légal FR)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"🔥 {NAME} NODE — {VERSION}")
    print(f"   Auteur : {AUTHOR}")

    identity = generate_or_load_identity(args.keys_dir)
    node_id = node_id_from_pub(identity.public_bytes)
    print(f"[+] node_id = {node_id}")
    print(f"[+] keys    = {identity.keys_dir}")

    if not args.no_mesh:
        try:
            result = setup_ibss_batman(
                iface=args.iface,
                ip_cidr=args.ip,
                dry_run=args.dry_run,
                txpower_dbm=args.txpower,
            )
            print(f"[+] mesh   = {result['ssid']} on {result['iface']} → {result['bat_iface']}")
            print(f"[+] ip     = {result['ip_cidr']} (dry_run={result['dry_run']})")
            if args.dry_run:
                print("[*] Étapes prévues :")
                for step in result["steps"]:
                    print(f"    {step}")
        except Exception as exc:
            print(f"[!] Setup mesh : {exc}", file=sys.stderr)
            if not args.dry_run:
                return 1

    bind_ip = "127.0.0.1" if args.dry_run and args.bind == "0.0.0.0" else args.bind
    transport = UdpTransport(
        bind_ip=bind_ip,
        port=args.port,
        identity=identity,
        broadcast=True,
    )
    print(f"[+] UDP    = {bind_ip}:{args.port}")
    print("[*] Beacons toutes les "
          f"{args.interval}s — Ctrl+C pour arrêter")

    try:
        while True:
            transport.send_discovery(BEACON)
            print(f"[beacon] {node_id} @ {time.strftime('%H:%M:%S')}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[+] Arrêt nœud.")
    finally:
        transport.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
