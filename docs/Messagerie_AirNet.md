# Messagerie AirNet — `airnet-msg`

## Rôle

Messagerie P2P sur le mesh : messages **scellés** (X25519 + ChaCha20-Poly1305)
vers un pair choisi, file offline `pending_messages.json`, découverte via PRESENCE.

Le mode **CLI** est le chemin fiable. `--gui` tente PyQt5 si l’extra `gui` est
installé ; sinon un message clair t’indique de rester en CLI.

## Framing MSG

```
AIR1 | type=MSG(3) | sender_pub(32) | sealed_blob
```

`sealed_blob = seal(texte_utf8, recipient_pub)` via `airnet.crypto`.

Les beacons / présence restent en clair (pas de secret dedans).

## Lancer

```bash
pip install -e .
# optionnel GUI :
pip install -e ".[gui]"

airnet-msg --no-mesh --bind 127.0.0.1 --listen 5
# puis : list | send <node_id> <texte> | listen 10 | quit

# one-shot
airnet-msg --no-mesh --bind 127.0.0.1 --to <node_id> -m "salut" --peer-addr 127.0.0.1
```

## File offline

Si le destinataire est inconnu / hors ligne, le texte est empilé dans
`pending_messages.json` et renvoyé quand le pair réapparaît.

## Ancien prototype

`legacy/pctamalou_airnet_messenger.py` (PyQt5 + Scapy + Chaos) — déprécié.
