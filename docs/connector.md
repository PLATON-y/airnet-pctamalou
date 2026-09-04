# Connecteur AirNet — `airnet-connect`

## Rôle

Rejoindre le mesh (ou partir du principe qu’il est déjà monté) et **découvrir**
les nœuds actifs via les trames **BEACON** / **PRESENCE** en UDP.

C’est ton ticket d’entrée : tu vérifies que le réseau vit avant de chatter.

## Stack

- Mesh : IBSS + batman-adv (`bat0`), option `--no-mesh` / `--dry-run`
- Transport : UDP `41337` sur l’IP de l’interface mesh (ou `127.0.0.1` en lab)
- Découverte : plaintext `AIR1` + type + node_id + clé publique X25519 + timestamp
- Crypto applicative : réservée à MSG/VOICE (`seal` / `open`) — pas sur les beacons

## Lancer

```bash
# Lab sans hardware
airnet-connect --no-mesh --dry-run --bind 127.0.0.1 --timeout 10

# Terrain
sudo airnet-connect --timeout 30
```

Tu obtiens la liste des `node_id` actifs (TTL configurable via `--stale`).

## Compatibilité

Chemin principal : **Linux**. Les anciens scripts Windows/Android sous `legacy/`
restent en musée ; une réécriture multi-OS viendra plus tard sur le même framing.

## Ancien prototype

`legacy/pctamalou_client_connector*.py` — Scapy sniff, déprécié.
