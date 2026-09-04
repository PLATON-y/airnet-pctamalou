"""Points d'entrée CLI AirNet (délèguent aux modules apps).

Console scripts (pyproject) :
- airnet-node    → airnet.apps.node:main
- airnet-connect → airnet.apps.connector:main
- airnet-msg     → airnet.apps.messenger:main
- airnet-voice   → airnet.apps.voice:main
- airnet-trust   → airnet.apps.trust_cli:main
- airnet-channel → airnet.apps.channel_cli:main
"""

from __future__ import annotations

from airnet.apps.channel_cli import main as channel_main
from airnet.apps.connector import main as connect_main
from airnet.apps.messenger import main as msg_main
from airnet.apps.node import main as node_main
from airnet.apps.trust_cli import main as trust_main
from airnet.apps.voice import main as voice_main

__all__ = [
    "node_main",
    "connect_main",
    "msg_main",
    "voice_main",
    "trust_main",
    "channel_main",
]


def airnet_node() -> None:
    raise SystemExit(node_main())


def airnet_connect() -> None:
    raise SystemExit(connect_main())


def airnet_msg() -> None:
    raise SystemExit(msg_main())


def airnet_voice() -> None:
    raise SystemExit(voice_main())


def airnet_trust() -> None:
    raise SystemExit(trust_main())


def airnet_channel() -> None:
    raise SystemExit(channel_main())
