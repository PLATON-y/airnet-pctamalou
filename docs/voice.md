AirNet PCTamalou Voice – Appels Chiffrés, Liberté Totale

Platon-y pour PCTamalou – Mars 2025

Pourquoi des Appels sur AirNet ?

T’en as marre des applis qui écoutent ta voix, des serveurs qui stockent tes "allo" ? AirNet PCTamalou Voice, c’est TON téléphone, sans forfait, sans trace, juste toi et ton réseau. On a pris notre infra maillée, notre chiffrement de ouf, et on a ajouté des appels vocaux – sécurisés, bruts, libres.

C’est quoi, AirNet Voice ?

C’est un script (pctamalou_airnet_voice.py) qui te laisse causer en direct sur AirNet PCTamalou. Pas besoin d’Internet, pas de tour GSM – juste des nœuds, un micro, et notre algo PCTamalou.

    P2P : Toi à ton contact, direct, sans intermédiaire.
    Chiffré : Chaque mot est blindé avec AES-256, Chaos Sinusoïdal, et ECC.
    Multiplateforme : Linux, Windows, Android (rooté).
    CLI ou GUI : T’as le choix – ligne de commande ou fenêtre, au cas où le GUI foire.

Le Chiffrement : Toujours PCTamalou

Personne ne touche ta voix. On utilise le même algo que pour les messages :

    AES-256 : Base solide, incassable par force brute.
    Chaos Sinusoïdal : Des vagues tordues (sinus à 0.13) qui embrouillent tout – bonne chance pour suivre sans la clé !
    ECC (SECP256R1) : Signature unique par nœud – c’est toi, et rien d’autre.
    Chaque paquet audio (20-64ms) est chiffré, signé, envoyé. Intraçable, imparable.

Comment ça Marche ?

Fonctionnalités

    Détection Auto des Nœuds : Sniffe les beacons, te donne la liste des ShadowIDs actifs (timeout 30s).
    Qualité Audio Ajustable :
        Low : 8kHz, léger mais clair (64ms/paquet).
        Med : 16kHz, bon compromis (64ms/paquet).
        High : 44.1kHz, top son (23ms/paquet).
    CLI ou GUI :
        CLI : Tape un ShadowID, parle direct.
        GUI : Liste déroulante, boutons "Appeler/Stopper", fallback si ça plante.

Étapes

    Connexion : Se branche à AirNetPCTamalou (ad-hoc Wi-Fi, IP 10.13.37.X).
    Détection : Repère les nœuds actifs via beacons.
    Appel : Choisis un ShadowID, ton micro envoie, tes haut-parleurs jouent.
    Sécurité : Chaque paquet vocal est chiffré/déchiffré en temps réel.

Prérequis

    Matériel : Micro + haut-parleurs (testés sur PC, Android rooté).
    Logiciels :
        Python 3.7+
        Dépendances (voir requirements.txt) :
        pyaudio>=0.2.11 # Audio
        pyqt5>=5.15.6 # GUI
        scapy>=2.4.5 # Paquets
        cryptography>=3.4.8 # Chiffrement
        numpy>=1.21.0 # Chaos
        Linux : sudo apt install portaudio19-dev avant pip install pyaudio.
    Réseau : AirNet actif (nœuds via pctamalou_node_runner.py).

Utilisation

CLI

python3 src/pctamalou_airnet_voice.py --mode cli --quality high --target <ShadowID>

    Liste les nœuds actifs, tape un ShadowID ou passe-le en argument.
    Parle, Ctrl+C pour couper.

GUI

python3 src/pctamalou_airnet_voice.py --mode gui --quality med

    Fenêtre : Liste des nœuds (mise à jour toutes 5s), "Appeler", "Stopper".
    Si GUI plante (ex. : pas de bureau), relance en CLI.

Détails Techniques

Code Clé

    detect_nodes() : Sniffe les beacons, garde les nœuds vivants (< 30s).
    init_audio(quality) : Ouvre micro/haut-parleurs avec taux choisi.
    send_voice_packet(target_id, audio_data) : Envoie flux chiffré via Scapy.
    listen_voice_packets() : Reçoit, déchiffre, joue en live.

Qualité Audio

    Low : 512 frames, 8kHz – léger, pour faible bande passante.
    Med : 1024 frames, 16kHz – équilibré, bonne clarté.
    High : 1024 frames, 44.1kHz – max qualité, plus de données.

Limites & Futur

    Latence : Dépend de la portée (100m-15km) et du matos.
    Un seul appel : Pour l’instant, pas de multi-destinataires (à coder si tu veux !).
    Idées :
        Ajouter un "bip" style talkie-walkie.
        Support multi-appels ou conférences.
        Indicateur de qualité en GUI.

Contribue !

T’es chaud pour améliorer ?

    Code : Fork, ajoute des trucs, pull request sur https://github.com/PLATON-y/airnet-pctamalou.git.
    Feedback : Balance tes idées à admin@pctamalou.fr.
    Test : Fais tourner, dis-nous si ça claque chez toi !

Pourquoi c’est Génial ?

AirNet Voice, c’est ta voix, libre, sécurisée, hors système. Pas d’espions, pas de coupures – juste toi, tes contacts, et un réseau que TU contrôles. Dans un monde qui écoute tout, c’est notre cri de liberté.

Platon-y pour PCTamalou – Parle fort, parle vrai.
