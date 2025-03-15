2️⃣ Connecteur Android – pctamalou_client_connector_android.py

Rôle

Connecte un smartphone Android à AirNet PCTamalou et vérifie les nœuds actifs via leurs beacons. Simple, mobile, sécurisé.

Pourquoi ?

Ton phone dans la poche devient un accès à AirNet. Pas d’Internet, pas de Play Store – juste du P2P pur.

Détails Techniques

    Technologie :
        Wi-Fi IBSS (ad-hoc via root).
        Termux (Python sur Android).
        Chiffrement PCTamalou (pour beacons).

    Compatibilité : Android 7+ avec root (Magisk/custom ROM).

    Fonctionnement :
        Connexion à AirNet (canal 2412).
        Écoute beacons (timeout 30s).
        Sortie CLI.

Matériel Nécessaire

    Smartphone Android (~50-200€) : Xiaomi, Samsung, vieux modèles OK (Wi-Fi 2.4 GHz).
    Root Access : Magisk ou custom ROM (sans root, pas d’IBSS).
    Chargeur : Usage normal (~1-2h autonomie en sniff).
    Coût : 0€ si phone rooté, ~50€ pour un vieux rootable.

Préparation du Matériel

    Rooter le Téléphone :

        Vérifie : Google "[modèle] root" (ex. : "Samsung A50 root") sur xda-developers.com.

        Simple (Magisk) :
            Déverrouille bootloader (voir XDA).
            Installe TWRP (twrp.me).
            Flash Magisk ZIP (magisk.me) via TWRP (~15 min).

        Test : App "Root Checker" (F-Droid). Si "Not Rooted" : "Relisez XDA ou changez de phone."

    Installer Termux :
        Télécharge APK : github.com/termux (pas Play Store).
        Ouvre, mets à jour :

    pkg update && pkg upgrade -y

Dépendances :

    Termux :

        pkg install python clang libcrypt -y
        pip install cryptography numpy asyncio scapy
        Temps : ~5-10 min. Si échec : "Vérifiez connexion ou relancez."

    Vérifier Wi-Fi :
        iw dev.
        Sortie : wlan0. Si rien : "Root mal configuré ou Wi-Fi HS."

Le Script : pctamalou_client_connector_android.py

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

# 🔹 Interface Wi-Fi (fixée Android)
iface = "wlan0"
NETWORK_NAME = "AirNetPCTamalou"
CLIENT_IP = f"10.13.37.{random.randint(2, 254)}"
# Vérif IP
if os.system(f"ping -c 1 {CLIENT_IP}") == 0:
    print(f"Attention : IP {CLIENT_IP} prise. Relancez.")
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

# 🔹 Connexion
def connect_to_network():
    try:
        os.system(f"iw dev {iface} set type ibss")
        os.system(f"iw dev {iface} ibss join {NETWORK_NAME} 2412")
        os.system(f"ifconfig {iface} up {CLIENT_IP}/24")
        print(f"[+] Connected to AirNet – IP: {CLIENT_IP}")
    except Exception as e:
        print(f"Erreur connexion : {e}. Vérifiez root (su) ou Wi-Fi (iw dev).")

# 🔹 Écoute Beacons
async def listen_for_beacons():
    known_nodes = {}
    start_time = time.time()
    def handle_packet(pkt):
        if Raw in pkt and pkt[Dot11].type == 0 and pkt[Dot11].subtype == 8:
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
        print(f"Erreur sniff : {e}. Vérifiez root ou wlan0 (iw dev).")
    if not known_nodes and time.time() - start_time > 30:
        print("Aucun nœud après 30s. Vérifiez portée ou lancez un nœud près de vous.")

if __name__ == "__main__":
    print("🔥 AIRNET CLIENT CONNECTOR – ANDROID 🔥")
    print("Connexion à AirNet... (Root requis !)")
    connect_to_network()
    print("Listening for nodes... (30s max, Ctrl+C to stop)")
    asyncio.run(listen_for_beacons())

Comment Lancer ?

    Copier :
        Termux : nano pctamalou_client_connector_android.py.
        Copie-colle, sauvegarde (Ctrl+O, Enter, Ctrl+X).

    Permissions :
        chmod +x pctamalou_client_connector_android.py.

    Lancer :
        su -c "python pctamalou_client_connector_android.py".

        Sortie :

        🔥 AIRNET CLIENT CONNECTOR – ANDROID 🔥
        Connexion à AirNet... (Root requis !)
        [+] Connected to AirNet – IP: 10.13.37.X
        Listening for nodes... (30s max, Ctrl+C to stop)
        🎯 Active Nodes: 1 – Last: abcd1234...

Vérifications & Erreurs

    OK : Nœuds listés.
    "Permission denied" : Relance avec su.
    "No such device" : iw dev pour wlan0. Si vide : "Root échoué ou Wi-Fi HS."
    Rien après 30s : "Pas de nœuds à portée. Lancez un nœud près de vous."

Conseils

    Portée : 100m (Wi-Fi intégré), 1-5 km (USB + antenne).
    Batterie : Sniff consomme, branche si long usage.
