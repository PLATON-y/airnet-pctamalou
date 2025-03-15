2️⃣ Connecteur Windows – pctamalou_client_connector_windows.py

Rôle

Permet à un PC Windows de se connecter à AirNet PCTamalou et de vérifier les nœuds actifs en écoutant leurs beacons. C’est ta porte d’entrée sur Windows, simple et sécurisée.

Pourquoi ?

Windows est partout, et ce script te branche au réseau mesh sans Linux, juste avec un PC et une carte Wi-Fi USB. Parfait pour communiquer hors système.

Détails Techniques

    Technologie :
        Wi-Fi IBSS (ad-hoc, via carte USB car Windows natif est limité).
        Chiffrement PCTamalou (AES-256 + Chaos + ECC pour beacons).
        Python + Scapy (sniff réseau).

    Compatibilité : Windows 10/11 (7 possible avec tweaks).

    Fonctionnement :
        Connexion manuelle via GUI Windows.
        Écoute des beacons (timeout 30s).
        Sortie CLI.

Matériel Nécessaire

    PC Windows (~100-500€) : Laptop ou desktop avec USB.
    Carte Wi-Fi USB (~20-30€) : Alfa AWUS036NHA ou AWUS036ACH (chipsets Atheros/Realtek, mode monitor + IBSS).
    Alimentation : Secteur ou batterie laptop.
    Coût total : ~20-30€ si PC dispo, ~120€ avec PC d’occase.

Préparation du Matériel

    Installer Python :

        Télécharge : python.org (Python 3.11).

        Lance l’installateur :
            Coche "Add Python to PATH".
            Clique "Install Now" (~5 min).

        Vérifie (CMD : Touche Windows + R, cmd, Enter) :

    python --version

        Sortie : Python 3.11.X. Si erreur : réinstalle ou vérifie PATH.

Dépendances :

    CMD (admin : Ctrl+Shift+Enter) :

        pip install cryptography numpy asyncio scapy
        Temps : ~5-10 min. Si échec : "Vérifiez Internet ou tapez pip install --upgrade pip."

    Carte Wi-Fi USB :

        Branche (ex. : Alfa AWUS036NHA).

        Installe drivers :

            Télécharge sur alfa.com.tw.
            Exécute .exe (~5 min).

        Vérifie : Panneau de config > Réseau > Adaptateurs. Doit lister "Alfa USB Adapter".
        Si absent : "Rebranchez ou testez un autre port USB."

    Connexion Manuelle :

        Clique icône Wi-Fi (barre tâches).

        Crée réseau :
            Nom : AirNetPCTamalou.
            Sécurité : Ouverte (pas de mot de passe).
            Connecte-toi avant lancement.

        Si introuvable : "Redémarrez Wi-Fi ou utilisez logiciel Alfa."

Le Script : pctamalou_client_connector_windows.py

import os
import time
import random
import asyncio
from scapy.all import *
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import numpy as np

# 🔹 Interface Wi-Fi (à ajuster)
# Exécutez "netsh wlan show interfaces" pour trouver le nom
iface = "Wi-Fi"  # Remplacez par "Wi-Fi 2" ou nom exact
NETWORK_NAME = "AirNetPCTamalou"
CLIENT_IP = f"10.13.37.{random.randint(2, 254)}"
# Vérif IP (basique)
if os.system(f"ping -n 1 {CLIENT_IP}") == 0:
    print(f"Attention : IP {CLIENT_IP} déjà prise. Relancez.")
    exit(1)

# 🔹 Chiffrement PCTamalou
def pctamalou_decrypt(ciphertext, sender_public_key):
    salt, iv, encrypted, signature = ciphertext[:16], ciphertext[16:32], ciphertext[32:-64], ciphertext[-64:]
    sender_public_key.verify(signature, encrypted, ec.ECDSA(hashes.SHA256()))
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(b"Platon-y_Air")
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted) + decryptor.finalize()
    data_array = np.frombuffer(padded_data.rstrip(b"\x00"), dtype=np.uint8)
    chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
    decrypted = np.bitwise_xor(data_array, chaos.astype(np.uint8))
    return decrypted.tobytes()

# 🔹 Connexion (manuelle + IP)
def connect_to_network():
    try:
        os.system(f"netsh interface ip set address name=\"{iface}\" static {CLIENT_IP} 255.255.255.0")
        print(f"[+] IP Configured – IP: {CLIENT_IP}")
        print("Vérifiez connexion à 'AirNetPCTamalou' dans Paramètres Wi-Fi !")
    except Exception as e:
        print(f"Erreur IP : {e}. Lancez CMD en admin ou vérifiez nom interface.")

# 🔹 Écoute Beacons
async def listen_for_beacons():
    known_nodes = {}
    start_time = time.time()
    def handle_packet(pkt):
        if Raw in pkt and pkt[Dot11].type == 0 and pkt[Dot11].subtype == 8:  # Beacon
            try:
                pub_key_pem = pkt[Raw].load[-256:]
                pub_key = serialization.load_pem_public_key(pub_key_pem)
                decrypted = pctamalou_decrypt(pkt[Raw].load[:-256], pub_key).decode()
                if decrypted.startswith("BEACON:"):
                    node_id = decrypted.split(":")[1]
                    known_nodes[node_id] = time.time()
                    current_time = time.time()
                    active_nodes = {k: v for k, v in known_nodes.items() if current_time - v < 30}
                    print(f"🎯 Active Nodes: {len(active_nodes)} – Last: {node_id}")
            except Exception:
                pass
    try:
        sniff(iface=iface, prn=handle_packet, store=0, timeout=30)
    except Exception as e:
        print(f"Erreur sniff : {e}. Vérifiez interface ou carte USB (mode monitor requis).")
    if not known_nodes and time.time() - start_time > 30:
        print("Aucun nœud après 30s. Vérifiez portée ou lancez un nœud près de vous.")

if __name__ == "__main__":
    print("🔥 AIRNET CLIENT CONNECTOR – WINDOWS 🔥")
    print("Préparez-vous : connectez-vous manuellement à 'AirNetPCTamalou' d’abord !")
    connect_to_network()
    print("Listening for nodes... (30s max, Ctrl+C to stop)")
    asyncio.run(listen_for_beacons())

Comment Lancer ?

    Copier :
        Clic droit > Nouveau > Document texte.
        Renomme : pctamalou_client_connector_windows.py.
        Ouvre avec Notepad, copie-colle, sauvegarde.

    Ajuster Interface :
        CMD : netsh wlan show interfaces.
        Note "Name" (ex. : "Wi-Fi 2"), remplace dans iface.
        Si introuvable : "Carte USB mal détectée. Vérifiez drivers."

    Lancer :
        CMD admin (Touche Windows + R, cmd, Ctrl+Shift+Enter) :

cd chemin\vers\dossier
python pctamalou_client_connector_windows.py

Sortie :

        🔥 AIRNET CLIENT CONNECTOR – WINDOWS 🔥
        Préparez-vous : connectez-vous manuellement à 'AirNetPCTamalou' d’abord !
        [+] IP Configured – IP: 10.13.37.X
        Listening for nodes... (30s max, Ctrl+C to stop)
        🎯 Active Nodes: 1 – Last: abcd1234...

Vérifications & Erreurs

    OK : Nœuds listés.
    "Interface not found" : Vérifie netsh wlan show interfaces, ajuste iface.
    "Permission" : Relance CMD en admin.
    Rien après 30s : "Pas de nœuds à portée. Lancez pctamalou_node_runner.py près de vous."
    Sniff échoue : "Carte USB incompatible ou drivers manquants. Testez Alfa AWUS036NHA."

Conseils

    Portée : 100m (intégré), 1-5 km (USB + antenne).
    Connexion : Fais-la manuelle avant, Windows natif ne gère pas IBSS bien.
