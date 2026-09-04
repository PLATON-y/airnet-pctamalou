# Confiance AirNet — sur-protection des utilisateurs

Version **0.4.0-trust**. Politique : **default DENY**.

## Modèle utilisateur

1. Des personnes qui se connaissent échangent des clés **hors bande (OOB)** :
   - secret partagé (passphrase / 32 octets), **et/ou**
   - acceptation mutuelle (ou unilatérale) des clés publiques X25519.
2. Ensuite elles peuvent parler : **personne d’autre** ne peut lire.
3. Fonctionne pour des **groupes** (N personnes), pas seulement des paires.
4. **Confiance directionnelle** : un appareil peut SEND+RECV, ou RECV-ONLY
   s’il a accepté le pair sans réciproque.
5. Privatisation : **refuser par défaut** tant qu’il n’y a pas d’acceptation.

## Échange OOB (hors bande)

Ne passe **pas** par le mesh radio ouvert (IBSS). Exemples :

| Moyen | Usage |
|-------|--------|
| QR code | Afficher / scanner la clé publique ou le secret de canal *(QR à venir)* |
| USB / fichier | Copier `identity.x25519.pub` ou le secret `.secret` |
| Oral / papier | Dicter une passphrase de canal |
| Signal / autre messagerie déjà de confiance | Envoyer la pub hex ou le secret une fois |

**Jamais** coller un secret de canal dans un log, un ticket ou un chat public.

## Accepter un pair (messages scellés pairwise)

```bash
# Voir sa propre clé publique
xxd -p -c 32 ~/.config/airnet/keys/identity.x25519.pub

# Accepter la clé d’un ami (reçue OOB)
airnet-trust accept --pub <HEX64>
airnet-trust accept --file ~/ami.pub --name Alice
airnet-trust list
airnet-trust revoke --node-id <16hex>
```

- `accepted=True` ⇒ **tu déchiffres** ses MSG/VOICE.
- S’il ne t’a pas accepté ⇒ **il ignore** tes messages (sens unique).
- Les BEACON/PRESENCE restent visibles comme `unknown` pour la découverte ;
  le chat reste bloqué tant que tu n’as pas accepté.

### Confiance à sens unique

```
A accepte B ; B n’accepte pas A
→ B → A : A ouvre (OK)
→ A → B : B droppe (ignored untrusted)
```

A est en **réception seule** vis-à-vis de B jusqu’à ce que B accepte A.

## Canaux à secret partagé (PSK)

Idéal pour un groupe qui s’est mis d’accord sur une « clé à eux » :

```bash
# Créer (génère un secret aléatoire — à montrer une fois)
airnet-channel create --name soiree --type group --show-secret

# Les autres rejoignent avec le MÊME nom + secret (OOB)
airnet-channel join --name soiree --secret '…'
airnet-channel list
airnet-channel send --channel soiree "on se retrouve au bat0"
```

- Dérivation : `HKDF-SHA256(secret, salt="AirNet-channel-v1", info=channel_id)`
- AEAD : ChaCha20-Poly1305 (pas d’ECDH)
- Types : `pair` ou `group` (même crypto)
- Membership = **connaître le secret**
- Fichier secret en mode `0o600` ; jamais loggé en clair

Trame : `AIR1 | 5 | channel_id_16 | blob`

## Messagerie

```bash
airnet-msg --no-mesh --bind 127.0.0.1
# accept <pub_hex>
# send <node_id> …
# channel <nom> …
```

Envoi pairwise : destinataire **accepté** (ou `--channel`).
Réception : default DENY sauf acceptation.


