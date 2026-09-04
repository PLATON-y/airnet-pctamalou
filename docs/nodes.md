# Nœuds AirNet — `airnet-node`

## Rôle

Transforme une machine Linux (ex. Raspberry Pi) en **nœud** du mesh AirNet PCTamalou :
configuration IBSS + batman-adv, IP sur `bat0`, beacons UDP périodiques.

Le **routage / relais L2** est le travail de **batman-adv** — le processus Python
annonce seulement sa présence (trames BEACON en clair) et reste actif.

## Stack actuelle (0.3.0-rewrite)

| Couche | Techno |
|--------|--------|
| Radio | Wi-Fi IBSS (ad-hoc), SSID `AirNetPCTamalou`, 2412 MHz |
| Mesh | batman-adv → interface `bat0` |
| Transport | **UDP** port `41337` (pas de Scapy / RadioTap pour le trafic applicatif) |
| Crypto | `airnet.crypto` — X25519 + ChaCha20-Poly1305 (Phase 1) |
| Découverte | BEACON plaintext : magic `AIR1` + pub + node_id + timestamp |

## Légalité radio (FR / UE)

- Puissance TX max acceptée par le package : **20 dBm**.
- Ne **jamais** faire `iw reg set BO` ni contourner le domaine réglementaire.
- Par défaut, le driver garde sa puissance ; `--txpower` optionnel et plafonné.

## Installation rapide

```bash
pip install -e ".[dev]"
sudo apt install iw batctl batman-adv-dkms   # outils mesh
```

## Lancer

```bash
# Planification sans root (tests)
airnet-node --dry-run --no-mesh --bind 127.0.0.1

# Sur le terrain (root pour iw / batctl)
sudo airnet-node --iface wlan0
# ou IP fixe :
sudo airnet-node --ip 10.13.37.10/24
```

Sortie attendue : `node_id` (16 hex), IP `bat0`, beacons toutes les 10 s.

## Matériel (indicatif)

- Raspberry Pi 3/4 + carte Wi-Fi USB compatible IBSS (ex. Alfa)
- Antenne adaptée, alim stable
- Respecte toujours la réglementation locale

## Ancien prototype

`legacy/pctamalou_node_runner.py` (Scapy / Chaos) est **déprécié** — musée uniquement.
