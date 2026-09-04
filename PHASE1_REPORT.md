# Rapport Phase 1 — AirNet PCTamalou

**Date :** 4 septembre 2026 (PT)  
**Auteur travaux :** rebuild sur filesystem box  
**Version package :** `0.2.0-phase1`

## Objectif

Poser un socle Python installable (`airnet`) avec une cryptographie réelle,
sans réécrire encore le mesh Scapy ni la messagerie PyQt.

## Ce qui a changé

### Nouveau package `airnet/`

| Fichier | Rôle |
|---------|------|
| `airnet/identity.py` | Constantes NAME, VERSION, AUTHOR, ORGS, URLS, CONTACTS |
| `airnet/crypto/keys.py` | Identité X25519, persistance dir/fichiers sécurisés |
| `airnet/crypto/sealed.py` | `seal` / `open` (AEAD + en-tête de version) |
| `airnet/config/defaults.yaml` | Défauts projet / crypto / placeholder mesh |

### Packaging & qualité

- `pyproject.toml` : package `airnet`, dépendance `cryptography`, extra `dev` → pytest
- `tests/test_identity.py`, `tests/test_crypto_roundtrip.py`
- `AUTHORS`, `SECURITY.md`
- `README.md` mis à jour (affiliation, réécriture, roadmap, install/test)

### Legacy

- Contenu de `src/*.py` **déplacé** vers `legacy/`
- En-tête une ligne : `DEPRECATED: … use the airnet package`
- Répertoire `src/` retiré

### Documentation nœuds

- Dans `docs/nodes.md` : suppression du conseil `txpower 30` / `iw reg set BO`
- Remplacé par une consigne de respect de la réglementation FR/UE (`txpower 20` typique)
- Les autres docs (why_airnet, voice, etc.) mentionnent encore l’ancien « Chaos » à titre historique ; nettoyage complet prévu en suivi doc

## Choix crypto

| Couche | Algorithme | Motif |
|--------|------------|--------|
| Identité / KEX | **X25519** (ECDH) | Moderne, rapide, courbe standard |
| KDF | **HKDF-SHA256** | Dérivation propre du secret partagé |
| AEAD | **ChaCha20-Poly1305** | Authentifié, pas de CBC, largement audité |

**Format blob v1 :** `version (1) ‖ nonce (12) ‖ ciphertext+tag`  
AAD = `version ‖ clé_publique_destinataire` pour lier le contexte.

**Explicitement exclus du chemin sécurisé :**

- AES-CBC
- XOR sinusoïdal (« Chaos »)
- clé en dur `b"Platon-y_Air"`

## Comment tester

```bash
cd /workspace/airnet/airnet-pctamalou-main
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

**Résultat :** `13 passed` (2026-09-04).

Environnement géré (PEP 668) : un venv est requis sur cette box.

Ou : `pip install cryptography pytest && pytest -q` (dans le venv).

## Suite — Phase 2 (`bat0`)

1. Intégration **batman-adv** / interface `bat0` (config réseau mesh légale)
2. Brancher beacons / relais sur `seal`/`open` (plus de crypto legacy)
3. Puis seulement : connecteurs et messagerie réécrits

## Licences

Inchangées : `LICENSE` (GPLv3) + `LICENSE-APCL.md`.
