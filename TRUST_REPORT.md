# Rapport Trust — AirNet 0.4.0-trust

**Date :** 4 septembre 2026 (PT)  
**Objectif :** sur-protection des utilisateurs (default DENY, OOB, canaux).

## Livré

| Composant | Chemin |
|-----------|--------|
| Trust store | `airnet/trust/contacts.py` |
| Canaux PSK | `airnet/crypto/channel.py` |
| Framing type 5 | `CHANNEL_MSG` dans `airnet/transport/framing.py` |
| CLI | `airnet-trust`, `airnet-channel` |
| Apps | messenger / connector / voice enforce accept ou canal |
| Docs | `docs/trust.md`, SECURITY.md, README |

## Politique

- **RECV** MSG/VOICE : `is_accepted(sender)` sinon drop (`ignored untrusted`)
- **SEND** pairwise : contact accepté requis (sinon `--channel`)
- **Canal** : membership = secret OOB ; groupe N personnes
- **Directionnel** : A⊃B sans B⊃A ⇒ B→A OK, A→B droppé
- Beacons OK sans trust (affichés `unknown` / `trusted`)

## Non-objectifs (respectés)

- Pas de `BASE_KEY` / `Platon-y_Air`
- Pas de claim « mesh radio chiffré »
- Pas de TX power illégal

## Tests ajoutés

- `tests/test_trust_directional.py`
- `tests/test_channel_psk_group.py`
- `tests/test_default_deny.py`
