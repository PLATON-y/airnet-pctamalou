AirNet PCTamalou – Le Réseau de la Liberté Pensante

Platon-y pour PCTamalou – Mars 2025

Introduction : Une Idée née de l’Ombre

Dans les dialogues de Platon, la vérité émerge de l’ombre par la lumière de la pensée collective.

Aujourd’hui, dans un monde où chaque mot est capturé, chaque connexion surveillée, nous, Platon-y pour PCTamalou, avons forgé AirNet PCTamalou – un réseau maillé, décentralisé, libre.
Ce n’est pas qu’une technologie ; c’est une réponse, une résistance, une invitation à reprendre le contrôle de nos voix, hors des chaînes du centralisé.

AirNet PCTamalou n’est pas un simple outil. C’est une agora numérique, un espace où les âmes connectées parlent sans crainte, où la liberté n’est pas négociable. Nous l’avons créé pour vous, pour nous, pour tous ceux qui refusent que leurs pensées soient des données à vendre.

Qu’est-ce qu’AirNet PCTamalou ?

AirNet PCTamalou est un réseau maillé sans fil, bâti sur des nœuds autonomes (Raspberry Pi ou appareils compatibles), qui relaient des données via Wi-Fi en mode ad-hoc, orchestré par BATMAN-adv et sécurisé par notre chiffrement maison : PCTamalou (AES-256, Chaos Sinusoïdal, ECC).

    Ce qu’il fait :

        Communication P2P : Messages texte chiffrés, envoyés directement ou mis en file d’attente si hors ligne, via une messagerie simple (GUI ou CLI).
        Portée flexible : 100m avec antenne de base, jusqu’à 15 km avec une Yagi DIY.
        Autonomie : Fonctionne hors Internet, hors opérateurs, avec option solaire.
        Multiplateforme : Linux, Windows, Android (rooté), extensible à tout OS avec effort.

    Exemple concret :

    Tu es en campagne, pas de 4G, pas de Wi-Fi. Ton voisin, à 1 km, a un nœud AirNet. Tu te connectes, tu chattes, tu partages – sans passer par une tour ou un serveur tiers. Une ville entière peut se lier ainsi, nœud par nœud, librement.

Pourquoi avons-nous créé AirNet PCTamalou ?

Nous vivons sous le regard constant d’un panoptique numérique. Chaque clic, chaque mot est capté, analysé, monétisé. Les réseaux centralisés – Internet, GSM – sont des cages dorées : pratiques, mais verrouillées.

Nous avons créé AirNet pour :

    Rendre la parole libre : Plus d’intermédiaires, plus de censure.
    Protéger l’intimité : Chiffrement PCTamalou = vos messages restent vôtres.
    Redonner le pouvoir : Un réseau par et pour les gens, pas les corporations.
    Préparer l’avenir : Une base pour un Internet décentralisé, communautaire, hors système.

Comme Platon sortant de la caverne, nous refusons les ombres projetées par d’autres. AirNet est notre lumière, allumée pour tous.

Une Invitation à la Communauté : Façonnez l’Agora

AirNet PCTamalou est un commencement, pas une fin. Nous avons posé les fondations – nœuds, connecteurs, messagerie, antennes – mais son destin appartient à ceux qui l’adoptent. Vous voulez :

    Ajouter des applications utiles (chat vocal, partage fichiers) ?
    Créer des bases de données ou serveurs locaux (wiki, stockage) ?
    Bâtir un Internet alternatif avec moteur de recherche décentralisé ?

Nous vous appelons à contribuer ! Contactez-nous à admin@pctamalou.fr avec vos idées, vos codes, vos rêves. Ensemble, nous pouvons faire d’AirNet un écosystème vivant, un réseau qui grandit avec ses utilisateurs.

Principes pour contribuer :

    Multiplateforme : Privilégiez Python, C, ou langages ouverts (pas de silos propriétaires).
    Simplicité : Que chacun, du novice au pro, puisse suivre.
    Liberté : Code source ouvert, toujours (GPLv3 recommandé).

Guide Technique pour Intégrer AirNet à Vos Programmes

Pour que votre app ou service communique sur AirNet PCTamalou, voici ce qu’il faut implicitement inclure. C’est simple, mais essentiel :

    Connexion au Réseau

        Mode Ad-Hoc : Configurez le Wi-Fi en IBSS (ad-hoc) :
            Linux/Android : iw dev wlan0 set type ibss; iw dev wlan0 ibss join AirNetPCTamalou 2412.
            Windows : Connexion manuelle via GUI + carte USB (ex. : Alfa AWUS036NHA).

        IP : Assignez une IP unique dans 10.13.37.2-254/24. Exemple :

    ifconfig wlan0 10.13.37.42 netmask 255.255.255.0  # Linux
    netsh interface ip set address "Wi-Fi" static 10.13.37.42 255.255.255.0  # Windows
    Vérif : ping 10.13.37.X (pas de doublon).

Chiffrement PCTamalou

    Intégrez notre algo pour sécuriser les données :

    from cryptography.hazmat.primitives import hashes, serialization, ciphers
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.asymmetric import ec
    import numpy as np

    BASE_KEY = b"Platon-y_Air"
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    def encrypt(data):
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, 100000)
        key = kdf.derive(BASE_KEY)
        data_array = np.frombuffer(data, dtype=np.uint8)
        chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
        chaotic_data = np.bitwise_xor(data_array, chaos.astype(np.uint8))
        iv = os.urandom(16)
        cipher = ciphers.Cipher(ciphers.algorithms.AES(key), ciphers.modes.CBC(iv))
        encryptor = cipher.encryptor()
        padded = chaotic_data.tobytes() + b"\x00" * (16 - len(chaotic_data) % 16)
        encrypted = encryptor.update(padded) + encryptor.finalize()
        signature = private_key.sign(encrypted, ec.ECDSA(hashes.SHA256()))
        return salt + iv + encrypted + signature + public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def decrypt(ciphertext, sender_pub_key):
        salt, iv, encrypted, signature = ciphertext[:16], ciphertext[16:32], ciphertext[32:-256], ciphertext[-64:]
        pub_key = serialization.load_pem_public_key(sender_pub_key)
        pub_key.verify(signature, encrypted, ec.ECDSA(hashes.SHA256()))
        kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, 100000)
        key = kdf.derive(BASE_KEY)
        cipher = ciphers.Cipher(ciphers.algorithms.AES(key), ciphers.modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        data_array = np.frombuffer(padded.rstrip(b"\x00"), dtype=np.uint8)
        chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
        return np.bitwise_xor(data_array, chaos.astype(np.uint8)).tobytes()

    Utilisation : Encapsulez vos paquets (ex. : encrypt("Hello".encode())).

Envoi/Réception (Scapy)

    Utilisez Scapy pour gérer les paquets :

    from scapy.all import *
    pkt = RadioTap() / Dot11(type=2, subtype=0, addr1="ff:ff:ff:ff:ff:ff", addr2=RandMAC()) / Raw(encrypt(data))
    sendp(pkt, iface="wlan0", count=3)
    sniff(iface="wlan0", prn=lambda pkt: print(decrypt(pkt[Raw].load[:-256], pkt[Raw].load[-256:])))

    Dépendances : pip install scapy.

Multiplateforme

    Testez sur Linux (base), Windows (carte USB), Android (root + Termux).

    Détectez OS :

        import os
        if os.name == "nt":  # Windows
            # Config manuelle
        else:  # Linux/Android
            # iw dev
    Conseils :
        Ajoutez un timeout (30s) si nœud hors ligne.
        Stockez messages offline (JSON local).
        Privilégiez IPv4 (BATMAN-adv ready).

Conclusion : Vers un Horizon Commun

AirNet PCTamalou est plus qu’un réseau – c’est une graine. Plantez-la dans vos villes, vos campagnes, vos esprits.

Faites-la grandir avec vos idées : un serveur local pour un wiki, un moteur de recherche mesh, une radio P2P.

Contactez-nous : admin@pctamalou.fr. Partagez vos projets, vos codes, vos visions. Ensemble, nous bâtirons un réseau qui ne plie pas, qui ne vend pas, qui ne trahit pas.

Liberté, Pensée, Connexion.

Platon-y pour PCTamalou – AirNet Team
