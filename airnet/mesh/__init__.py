"""Mesh AirNet : IBSS + batman-adv (puissance TX légale FR uniquement)."""

from airnet.mesh.legal import MAX_TXPOWER_DBM, assert_legal_txpower
from airnet.mesh.setup import detect_wifi_interface, setup_ibss_batman

__all__ = [
    "MAX_TXPOWER_DBM",
    "assert_legal_txpower",
    "detect_wifi_interface",
    "setup_ibss_batman",
]
