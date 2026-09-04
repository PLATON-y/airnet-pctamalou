# Sécurité — AirNet PCTamalou

## Statut

**Expérimental.** AirNet PCTamalou (**0.4.0-trust**) est un prototype de laboratoire.
Utilise-le uniquement sur du matériel et des fréquences que tu es autorisé à
exploiter (mesh / lab / réseau dont tu es propriétaire).

## Cadre légal radio (FR / UE)

- Respecte la puissance d’émission (EIRP) et le domaine réglementaire
  applicables en France et dans l’Union européenne.
- **Ne** contourne **pas** les limites via un domaine réglementaire étranger
  (ex. `iw reg set BO`) ni via un `txpower` illégal.
- Ce package refuse `txpower > 20` dBm (`airnet.mesh.legal`).
- Aucun conseil visant à dépasser la réglementation radio locale.

## Confiance & confidentialité (0.4.0)

| Règle | Détail |
|-------|--------|
| Default DENY | MSG/VOICE d’un expéditeur non accepté → ignorés |
| Pas de mot de passe global | Aucune clé partagée « Platon-y_Air » / Chaos |
| Acceptation OOB | Clés publiques échangées hors bande, puis `airnet-trust accept` |
| Confiance directionnelle | A accepte B ≠ B accepte A |
| Canaux PSK | Secret de groupe/pair dérivé HKDF ; secret fichier 0o600 |
| Radio IBSS | **Non chiffrée** au niveau mesh — la confidentialité est applicative |

Voir [docs/trust.md](docs/trust.md).

## Cryptographie (chemin sécurisé)

| Élément | Choix |
|--------|--------|
| Identité nœud | X25519 (persistée, répertoire 0o700 / fichiers 0o600) |
| Pairwise | ECDH X25519 + HKDF-SHA256 + ChaCha20-Poly1305 (`seal`/`open`) |
| Canal PSK | HKDF-SHA256(secret, salt=`AirNet-channel-v1`) + ChaCha20-Poly1305 |
| Transport apps | UDP + framing `AIR1` ; types 3/4 scellés, type 5 canal |
| Formats exclus | AES-CBC, XOR « Chaos », clé en dur, Scapy app-routing |

Les scripts sous `legacy/` sont conservés pour référence historique uniquement —
**ne pas les utiliser** pour de nouvelles communications.

## Signalement

Contacte `admin@pctamalou.fr` ou `admin@e-of-h.fr` pour toute vulnérabilité.
Ne divulgue pas publiquement de détails exploitables avant coordination.
