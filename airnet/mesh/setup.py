"""Configuration IBSS + batman-adv pour AirNet.

Utilise ``subprocess.run(..., check=True)`` — jamais ``os.system``.
Mode ``dry_run=True`` : aucune commande root, retourne la liste des étapes prévues.
"""

from __future__ import annotations

import random
import shutil
import subprocess
from typing import Any

from airnet.mesh.legal import MAX_TXPOWER_DBM, assert_legal_txpower


DEFAULT_SSID = "AirNetPCTamalou"
DEFAULT_FREQ = 2412
DEFAULT_IP_PREFIX = "10.13.37"


class MeshSetupError(RuntimeError):
    """Échec de détection ou de configuration mesh."""


def _run(cmd: list[str], *, dry_run: bool, steps: list[str]) -> None:
    steps.append(" ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def detect_wifi_interface() -> str:
    """Détecte une interface Wi-Fi (wlan*) via ``iw dev``."""
    iw = shutil.which("iw")
    if not iw:
        raise MeshSetupError(
            "Outil 'iw' introuvable. Installe-le (ex. apt install iw) "
            "et branche une carte Wi-Fi compatible IBSS."
        )
    try:
        result = subprocess.run(
            [iw, "dev"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise MeshSetupError(f"Échec 'iw dev': {exc}") from exc

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Interface "):
            name = line.split()[1]
            if "wlan" in name:
                return name
    raise MeshSetupError(
        "Aucune interface Wi-Fi détectée. Branche une carte USB "
        "(ex. Alfa AWUS036ACH) et vérifie avec 'iw dev' / 'lsusb'."
    )


def _allocate_ip(ip_cidr: str | None, *, dry_run: bool) -> str:
    """Retourne un CIDR 10.13.37.X/24 (X aléatoire 2–254, ping check si possible)."""
    if ip_cidr:
        return ip_cidr

    for _ in range(16):
        host = random.randint(2, 254)
        ip = f"{DEFAULT_IP_PREFIX}.{host}"
        cidr = f"{ip}/24"
        if dry_run:
            return cidr
        # ping once ; si succès → IP prise, sinon on prend
        ping = shutil.which("ping")
        if not ping:
            return cidr
        proc = subprocess.run(
            [ping, "-c", "1", "-W", "1", ip],
            capture_output=True,
        )
        if proc.returncode != 0:
            return cidr
    raise MeshSetupError("Impossible d'allouer une IP libre sur 10.13.37.0/24")


def _check_batman_tools(*, dry_run: bool) -> None:
    if dry_run:
        return
    if not shutil.which("batctl"):
        raise MeshSetupError(
            "batman-adv / batctl introuvable. Installe les outils "
            "(ex. apt install batctl batman-adv-dkms) puis réessaie."
        )
    if not shutil.which("iw"):
        raise MeshSetupError("Outil 'iw' introuvable (apt install iw).")


def setup_ibss_batman(
    iface: str | None = None,
    ssid: str = DEFAULT_SSID,
    freq: int = DEFAULT_FREQ,
    ip_cidr: str | None = None,
    *,
    dry_run: bool = False,
    txpower_dbm: int | None = None,
) -> dict[str, Any]:
    """Configure IBSS + batman-adv et assigne une IP sur bat0.

    Parameters
    ----------
    iface :
        Interface Wi-Fi. Si None, auto-détection (ou ``wlan0`` en dry_run).
    ssid, freq :
        Paramètres IBSS (défaut AirNetPCTamalou @ 2412 MHz).
    ip_cidr :
        IP/CIDR explicite (ex. ``10.13.37.42/24``). Sinon allocation aléatoire.
    dry_run :
        Si True, n'exécute aucune commande root ; retourne les étapes prévues.
    txpower_dbm :
        Optionnel. Uniquement si ≤ 20 dBm. Par défaut : laisser le driver.

    Returns
    -------
    dict
        ``iface``, ``ssid``, ``freq``, ``ip_cidr``, ``bat_iface``, ``steps``, ``dry_run``.
    """
    steps: list[str] = []

    if iface is None:
        if dry_run:
            iface = "wlan0"
            steps.append(f"# detect_wifi_interface() → {iface} (simulé)")
        else:
            iface = detect_wifi_interface()
            steps.append(f"# detect_wifi_interface() → {iface}")

    _check_batman_tools(dry_run=dry_run)
    cidr = _allocate_ip(ip_cidr, dry_run=dry_run)
    bat_iface = "bat0"

    if txpower_dbm is not None:
        assert_legal_txpower(txpower_dbm)

    # batman-adv + IBSS
    _run(["modprobe", "batman-adv"], dry_run=dry_run, steps=steps)
    _run(["ip", "link", "set", iface, "down"], dry_run=dry_run, steps=steps)
    _run(["iw", "dev", iface, "set", "type", "ibss"], dry_run=dry_run, steps=steps)
    _run(["ip", "link", "set", iface, "up"], dry_run=dry_run, steps=steps)
    _run(
        ["iw", "dev", iface, "ibss", "join", ssid, str(freq)],
        dry_run=dry_run,
        steps=steps,
    )
    _run(["batctl", "if", "add", iface], dry_run=dry_run, steps=steps)
    _run(["ip", "link", "set", bat_iface, "up"], dry_run=dry_run, steps=steps)
    _run(
        ["ip", "addr", "add", cidr, "dev", bat_iface],
        dry_run=dry_run,
        steps=steps,
    )

    if txpower_dbm is not None:
        # iwconfig ou iw — jamais reg set BO
        _run(
            ["iw", "dev", iface, "set", "txpower", "fixed", f"{int(txpower_dbm) * 100}"],
            dry_run=dry_run,
            steps=steps,
        )
        steps.append(
            f"# txpower plafonné à {MAX_TXPOWER_DBM} dBm (légal FR) — pas de reg BO"
        )

    return {
        "iface": iface,
        "ssid": ssid,
        "freq": freq,
        "ip_cidr": cidr,
        "bat_iface": bat_iface,
        "steps": steps,
        "dry_run": dry_run,
        "txpower_dbm": txpower_dbm,
    }
