2️⃣ Programme Connecteur – pctamalou_client_connector.py

Rôle

Connecte un appareil (PC, laptop, etc.) à AirNet PCTamalou et vérifie les nœuds actifs via leurs beacons. C’est ton ticket d’entrée au réseau.

Pourquoi ?

Simple, universel, indispensable avant de chatter. Confirme que le réseau vit, sans besoin d’être un geek.

Détails Techniques

    Technologie :
        Wi-Fi IBSS (ad-hoc).
        Chiffrement PCTamalou (pour déchiffrer les beacons).

    Compatibilité : Linux (base), Windows/Android (ajustements, fichiers connexes).

    Fonctionnement :
        Détecte l’interface Wi-Fi.
        Rejoint AirNet avec IP unique (10.13.37.X).
        Écoute les beacons (timeout 30s).

Matériel Nécessaire

    Appareil Wi-Fi : PC/Linux, laptop, ou carte USB (~20€, ex. : Alfa AWUS036NHA).
    OS : Linux (Ubuntu, Raspbian), Windows (tweaks), Android (root).
    Coût : 0€ si matos existant, ~20€ avec USB.

Préparation du Matériel

    Linux :
        Installe : Ubuntu/Debian via ISO (usb.org) ou Raspbian (voir Nœuds).

        Dépendances :

    sudo apt update && sudo apt upgrade -y
    sudo apt install python3 python3-pip iw -y
    pip3 install cryptography numpy asyncio scapy
    Vérifie Wi-Fi : iw dev (doit lister wlanX).

Windows :

    Carte USB obligatoire (ex. : Alfa AWUS036NHA).
    Drivers : Site fabricant (ex. : alfa.com.tw).
    Python : python.org, coche "Add to PATH".

    CMD :

        pip install cryptography numpy asyncio scapy
        IBSS : Connexion manuelle (voir script Windows).

Le Script : pctamalou_client_connector.py

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

# 🔹 Auto-détection Wi-Fi
def detect_wifi_interface():
    interfaces = os.popen("iw dev | grep Interface | awk '{print $2}'").read().strip().split("\n")
    for iface in interfaces:
        if iface and "wlan" in iface:
            return iface
    if os.name == "nt":
        return "Wi-Fi"  # Ajustez via 'netsh wlan show interfaces'
    raise Exception("Erreur : Pas de Wi-Fi. Branchez une carte USB (ex. Alfa AWUS036NHA) et vérifiez 'iw dev' ou 'netsh'.")

iface = detect_wifi_interface()
NETWORK_NAME = "AirNetPCTamalou"
CLIENT_IP = f"10.13.37.{random.randint(2, 254)}"
# Vérif IP (basique)
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
        print(f"Erreur connexion : {e}. Vérifiez sudo, Wi-Fi, ou connexion manuelle (Windows).")

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
    sniff(iface=iface, prn=handle_packet, store=0, timeout=30)
    if not known_nodes and time.time() - start_time > 30:
        print("Aucun nœud détecté après 30s. Vérifiez portée ou nœuds actifs.")

if __name__ == "__main__":
    print("🔥 AIRNET CLIENT CONNECTOR 🔥")
    print("Connecting to AirNet PCTamalou...")
    connect_to_network()
    print("Listening for nodes... (30s max, Ctrl+C to stop)")
    asyncio.run(listen_for_beacons())

Comment Lancer ?

    Copier :
        nano pctamalou_client_connector.py, copie-colle, sauvegarde.

    Permissions :
        chmod +x pctamalou_client_connector.py.

    Lancer :
        sudo python3 pctamalou_client_connector.py.
        Sortie : (attendu)

        🔥 AIRNET CLIENT CONNECTOR 🔥
        Connecting to AirNet PCTamalou...
        [+] Connected to AirNet – IP: 10.13.37.X
        Listening for nodes... (30s max, Ctrl+C to stop)
        🎯 Active Nodes: 1 – Last: abcd1234...

Vérifications & Erreurs

    OK : Nœuds listés.
    "No Wi-Fi interface" : Vérifie iw dev (Linux) ou carte USB (Windows).
    "Permission denied" : sudo oublié.
    Rien après 30s : "Pas de nœuds à portée. Lancez pctamalou_node_runner.py près de vous."
    Windows : Connexion manuelle via GUI Wi-Fi avant lancement.

Conseils

    Portée : 100m (Wi-Fi intégré), 1-5 km (USB + antenne).
    Placement : Près d’un nœud, évite murs/métal.
