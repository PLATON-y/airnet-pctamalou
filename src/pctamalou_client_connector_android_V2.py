#!/data/data/com.termux/files/usr/bin/python
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

# 🔹 Config
iface = "wlan0"
NETWORK_NAME = "AirNetPCTamalou"
CLIENT_IP = f"10.13.37.{random.randint(2, 254)}"
# Vérif IP (simulée sans root)
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
    return np.bitwise_xor(data_array, chaos.astype(np.uint8)).tobytes()

# 🔹 Connexion
def connect_to_network():
    if os.geteuid() != 0:
        print("⚠️ Pas de root ! Mode passif activé. Rejoignez 'AirNetPCTamalou' manuellement via Wi-Fi.")
        return False
    try:
        os.system(f"iw dev {iface} set type ibss")
        os.system(f"iw dev {iface} ibss join {NETWORK_NAME} 2412")
        os.system(f"ifconfig {iface} up {CLIENT_IP}/24")
        print(f"[+] Connected to AirNet – IP: {CLIENT_IP}")
        return True
    except Exception as e:
        print(f"❌ Erreur connexion : {e}. Vérifiez root (su) ou Wi-Fi (iw dev).")
        return False

# 🔹 Écoute Beacons (Mode Passif + Combiné)
async def listen_for_beacons():
    known_nodes = {}
    start_time = time.time()
    def handle_packet(pkt):
        if Raw in pkt and pkt[Dot11].type == 0 and pkt[Dot11].subtype == 8:
            try:
                raw_data = pkt[Raw].load
                # Détection du beacon combiné (INVITE || BEACON)
                if b"||" in raw_data:
                    invite_part, encrypted_part = raw_data.split(b"||", 1)
                    if invite_part.startswith(b"INVITE:"):
                        node_id = invite_part.decode().split(":")[1]
                        known_nodes[node_id] = time.time()
                        print(f"🎯 Nœud détecté (INVITE): {node_id}")
                    # Tentative de décryptage BEACON (si root/mode monitor)
                    if len(encrypted_part) > 256:
                        pub_key_pem = encrypted_part[-256:]
                        pub_key = serialization.load_pem_public_key(pub_key_pem)
                        decrypted = pctamalou_decrypt(encrypted_part[:-256], pub_key).decode()
                        if decrypted.startswith("BEACON:"):
                            node_id = decrypted.split(":")[1]
                            known_nodes[node_id] = time.time()
                            print(f"🎯 Nœud détecté (BEACON): {node_id}")
                elif raw_data.startswith(b"INVITE:"):  # Compatibilité ancienne version
                    node_id = raw_data.decode().split(":")[1]
                    known_nodes[node_id] = time.time()
                    print(f"🎯 Nœud détecté (INVITE seul): {node_id}")
            except Exception:
                pass
    try:
        sniff(iface=iface, prn=handle_packet, store=0, timeout=15)
    except Exception as e:
        print(f"⚠️ Sniff limité : {e}. Sans root, seul 'INVITE' fonctionne. Vérifiez mode monitor.")
    if not known_nodes and time.time() - start_time > 15:
        print("Aucun nœud après 15s. Vérifiez portée ou un nœud actif nearby.")

# 🔹 Boucle Principale Termux-Friendly
def main():
    print("🔥 AIRNET TERMUX CONNECTOR – Bienvenue, nomade ! 🔥")
    if os.geteuid() != 0:
        print("❌ Pas de root ! Mode passif activé. Les nœuds doivent envoyer 'INVITE'.")
    else:
        print("[+] Root détecté, mode actif possible.")
        if not connect_to_network():
            print("⚠️ Mode passif forcé, connexion manuelle requise.")

    while True:
        print("\n=== Menu AirNet ===")
        print("1. Scanner les nœuds actifs")
        print("2. Quitter")
        choice = input("Choix : ")

        if choice == "1":
            print("[👀 Scanning... (15s max)]")
            asyncio.run(listen_for_beacons())
        elif choice == "2":
            print("👋 À bientôt, libre voyageur !")
            break
        else:
            print("❌ Option invalide, réessayez !")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Arrêt propre, nomade !")
        exit(0)
    except Exception as e:
        print(f"❌ Erreur : {e}. Vérifiez Termux, root, ou wlan0.")
        exit(1)
