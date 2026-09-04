# Rapport de réécriture — AirNet PCTamalou 0.3.0-rewrite

**Date :** 4 septembre 2026 (PT)  
**Auteur :** Platon-Y (Jonathan Ducros) — orgs PCTamalou + Echoes of Hackers  
**Sites :** https://pctamalou.fr · https://e-of-h.fr

## Objectif

Remplacer le stack legacy Scapy / RadioTap / Chaos XOR / AES-CBC par une
architecture cohérente autour de `airnet.crypto` (Phase 1) :

| Couche | Choix |
|--------|--------|
| Crypto | X25519 + HKDF-SHA256 + ChaCha20-Poly1305 (`seal` / `open` inchangés) |
| Mesh | IBSS + batman-adv → `bat0` |
| Transport | UDP port 41337, framing `AIR1` |
| Apps | node, connector, messenger, voice |

## Mapping ancien → nouveau

| Ancien fichier | Nouveau module / CLI |
|----------------|----------------------|
| `legacy/pctamalou_node_runner.py` | `airnet/apps/node.py` → `airnet-node` |
| `legacy/pctamalou_client_connector.py` | `airnet/apps/connector.py` → `airnet-connect` |
| `legacy/pctamalou_client_connector_windows.py` | *(conservé musée)* ; chemin Linux via `airnet-connect` |
| `legacy/pctamalou_client_connector_android.py` | *(conservé musée)* ; même framing à porter plus tard |
| `legacy/pctamalou_airnet_messenger.py` | `airnet/apps/messenger.py` → `airnet-msg` |
| `legacy/pctamalou_airnet_voice.py` | `airnet/apps/voice.py` → `airnet-voice` |
| Chaos / BASE_KEY / Scapy Dot11 apps | **supprimé du chemin sécurisé** (reste dans `legacy/` uniquement) |
| Setup `os.system` + `iw reg set BO` / txpower illégal | `airnet/mesh/setup.py` + `airnet/mesh/legal.py` (max 20 dBm) |

## Nouveaux modules

```
airnet/mesh/legal.py       # MAX_TXPOWER_DBM = 20
airnet/mesh/setup.py       # detect_wifi_interface, setup_ibss_batman (dry_run)
airnet/transport/framing.py
airnet/transport/udp.py    # UdpTransport + seal/open
airnet/apps/node.py
airnet/apps/connector.py
airnet/apps/messenger.py
airnet/apps/voice.py
airnet/cli.py              # wrappers / doc entry points
```

## Framing (résumé)

- **BEACON / PRESENCE** : plaintext `AIR1 \| type \| node_id(16 hex) \| pub(32) \| ts \| body`
- **MSG / VOICE** : `AIR1 \| type \| sender_pub(32) \| seal(plaintext, recipient_pub)`

## Packaging

- Version : `0.3.0` (`identity.VERSION = "0.3.0-rewrite"`)
- Console scripts : `airnet-node`, `airnet-connect`, `airnet-msg`, `airnet-voice`
- Extras : `dev` (pytest), `gui` (PyQt5), `voice` (PyAudio)

## Tests

- Conservés : `test_crypto_roundtrip.py`, `test_identity.py` (version mise à jour)
- Ajoutés : `test_framing.py`, `test_udp_localhost.py`, `test_mesh_dry_run.py`

```bash
.venv/bin/pytest -q
```

## Docs

- `docs/nodes.md`, `docs/connector.md`, `docs/Messagerie_AirNet.md` réécrits (FR, tutoiement)
- `README.md` : roadmap rewrite logiciel en cours ; hardware ensuite
- `legacy/` **non supprimé**

## Explicitement exclu

- Réintroduction Chaos XOR / `BASE_KEY` / Scapy pour le trafic applicatif
- Suggestions de TX power illégal ou `iw reg set BO`
- Dépendance hard à PyQt5 / Scapy sur le chemin core
