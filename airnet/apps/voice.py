"""CLI voix AirNet — VOICE scellé avec mêmes règles trust/canal que MSG.

Si ``pyaudio`` est absent : message d'installation clair et exit non-zéro.
Sinon : envoi de chunks audio scellés vers un pair accepté (ou canal PSK).
"""

from __future__ import annotations

import argparse
import sys
import time

from airnet.crypto.channel import ChannelStore, default_channels_dir
from airnet.crypto.keys import generate_or_load_identity
from airnet.identity import AUTHOR, NAME, VERSION
from airnet.transport.framing import VOICE, node_id_from_pub
from airnet.transport.udp import DEFAULT_PORT, UdpTransport
from airnet.trust.contacts import TrustStore, default_trust_dir


def _have_pyaudio() -> bool:
    try:
        import pyaudio  # noqa: F401

        return True
    except ImportError:
        return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="airnet-voice",
        description=f"{NAME} — voix scellée (trust / canal)",
    )
    p.add_argument("--keys-dir", default=None)
    p.add_argument("--trust-dir", default=None)
    p.add_argument("--channels-dir", default=None)
    p.add_argument("--bind", default="127.0.0.1")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--to-pub", default=None, help="Clé publique destinataire (hex 64)")
    p.add_argument("--channel", "-c", default=None, help="Canal PSK (nom)")
    p.add_argument("--peer-addr", default="127.0.0.1", help="IP du pair")
    p.add_argument(
        "--demo-chunk",
        action="store_true",
        help="Envoie un chunk factice sans micro (test framing)",
    )
    p.add_argument(
        "--skip-trust-check",
        action="store_true",
        help="(tests) autorise l'envoi sans contact accepté",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"🔥 {NAME} VOICE — {VERSION}")
    print(f"   Auteur : {AUTHOR}")

    identity = generate_or_load_identity(args.keys_dir)
    my_id = node_id_from_pub(identity.public_bytes)
    trust = TrustStore(args.trust_dir or default_trust_dir(identity.keys_dir))
    channels = ChannelStore(args.channels_dir or default_channels_dir(identity.keys_dir))
    print(f"[+] node_id = {my_id}")

    if args.demo_chunk:
        chunk = b"VOICE-DEMO-CHUNK\x00" + str(time.time()).encode()
        with UdpTransport(
            bind_ip=args.bind,
            port=args.port,
            identity=identity,
            broadcast=False,
            trust=trust,
            channels=channels,
        ) as transport:
            if args.channel:
                meta = channels.get(args.channel)
                if meta is None:
                    print(f"[!] Canal inconnu : {args.channel}", file=sys.stderr)
                    return 2
                transport.send_channel(
                    chunk,
                    channel_name=meta.name,
                    addr=(args.peer_addr, args.port),
                )
                print(f"[+] Chunk VOICE via canal {meta.name} → {args.peer_addr}:{args.port}")
                return 0
            if not args.to_pub:
                print("[!] --to-pub ou --channel requis pour --demo-chunk", file=sys.stderr)
                return 2
            recipient = bytes.fromhex(args.to_pub)
            if not args.skip_trust_check and not trust.is_accepted(recipient):
                # Pour l'envoi : on exige que le destinataire soit un contact accepté
                # (tu as choisi de lui parler). Réception côté pair = s'il t'a accepté.
                print(
                    "[!] Destinataire non accepté localement.\n"
                    "    Accepte sa clé (OOB) : airnet-trust accept --pub …\n"
                    "    Ou utilise --channel / --skip-trust-check (tests).",
                    file=sys.stderr,
                )
                return 1
            transport.send_sealed(
                chunk,
                recipient,
                msg_type=VOICE,
                addr=(args.peer_addr, args.port),
            )
            print(f"[+] Chunk VOICE scellé envoyé → {args.peer_addr}:{args.port}")
        return 0

    if not _have_pyaudio():
        print(
            "[!] pyaudio manquant. Installe l'extra voix :\n"
            "    pip install 'airnet[voice]'\n"
            "    # ou : pip install pyaudio\n"
            "Le framing VOICE est prêt ; le capture micro nécessite pyaudio.",
            file=sys.stderr,
        )
        return 1

    import pyaudio  # type: ignore

    if not args.to_pub and not args.channel:
        print("[!] --to-pub ou --channel requis pour envoyer de la voix", file=sys.stderr)
        return 2

    if args.to_pub and not args.channel:
        recipient = bytes.fromhex(args.to_pub)
        if not args.skip_trust_check and not trust.is_accepted(recipient):
            print(
                "[!] Destinataire non accepté. airnet-trust accept --pub …",
                file=sys.stderr,
            )
            return 1
    else:
        recipient = b""

    rate = 16000
    channels_n = 1
    width = 2
    chunk_frames = 1024

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pa.get_format_from_width(width),
        channels=channels_n,
        rate=rate,
        input=True,
        frames_per_buffer=chunk_frames,
    )
    print("[*] Capture micro — Ctrl+C pour arrêter")
    transport = UdpTransport(
        bind_ip=args.bind,
        port=args.port,
        identity=identity,
        broadcast=False,
        trust=trust,
        channels=channels,
    )
    try:
        while True:
            data = stream.read(chunk_frames, exception_on_overflow=False)
            if args.channel:
                transport.send_channel(
                    data,
                    channel_name=args.channel,
                    addr=(args.peer_addr, args.port),
                )
            else:
                transport.send_sealed(
                    data,
                    recipient,
                    msg_type=VOICE,
                    addr=(args.peer_addr, args.port),
                )
    except KeyboardInterrupt:
        print("\n[+] Voix arrêtée.")
    finally:
        transport.close()
        stream.stop_stream()
        stream.close()
        pa.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
