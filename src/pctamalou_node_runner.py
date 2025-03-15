import os
import time
import random
import asyncio
import hashlib
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
    raise Exception("Erreur : Aucune interface Wi-Fi détectée. Branchez une carte USB (ex. Alfa AWUS036ACH) et vérifiez avec 'lsusb'.")

iface = detect_wifi_interface()
NETWORK_NAME = "AirNetPCTamalou"
BASE_KEY = b"Platon-y_Air"
NODE_IP = f"10.13.37.{random.randint(2, 254)}"
# Vérif IP unique (basique)
if os.system(f"ping -c 1 {NODE_IP}") == 0:
    print(f"Attention : IP {NODE_IP} déjà utilisée. Relancez le script.")
    exit(1)
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()
NODE_ID = hashlib.sha256(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()[:16]

# 🔹 Chiffrement PCTamalou
def pctamalou_encrypt(data, salt=os.urandom(16)):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(BASE_KEY)
    data_array = np.frombuffer(data, dtype=np.uint8)
    chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
    chaotic_data = np.bitwise_xor(data_array, chaos.astype(np.uint8))
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padded_data = chaotic_data.tobytes() + b"\x00" * (16 - len(chaotic_data) % 16)
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    signature = private_key.sign(encrypted, ec.ECDSA(hashes.SHA256()))
    return salt + iv + encrypted + signature

def pctamalou_decrypt(ciphertext, sender_public_key):
    salt, iv, encrypted, signature = ciphertext[:16], ciphertext[16:32], ciphertext[32:-64], ciphertext[-64:]
    sender_public_key.verify(signature, encrypted, ec.ECDSA(hashes.SHA256()))
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(BASE_KEY)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted) + decryptor.finalize()
    data_array = np.frombuffer(padded_data.rstrip(b"\x00"), dtype=np.uint8)
    chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
    decrypted = np.bitwise_xor(data_array, chaos.astype(np.uint8))
    return decrypted.tobytes()

# 🔹 Setup Mesh BATMAN-adv
def setup_mesh():
    os.system(f"modprobe batman-adv")
    os.system(f"iw dev {iface} set type ibss")
    os.system(f"iw dev {iface} ibss join {NETWORK_NAME} 2412")
    os.system(f"batctl if add {iface}")
    os.system(f"ifconfig {iface} up")
    os.system(f"ifconfig bat0 up {NODE_IP}/24")
    try:
        os.system(f"iwconfig {iface} txpower 30")
    except:
        print("Attention : txpower 30 refusé (limite légale ou driver). Essayez 'iw reg set BO' ou réduisez à 20.")
    print(f"[+] AirNet Mesh ON – IP: {NODE_IP} – NodeID: {NODE_ID}")

# 🔹 Beacon
async def send_beacon():
    while True:
        pkt = RadioTap() / Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff", addr2=RandMAC(), addr3=RandMAC()) / \
              Raw(pctamalou_encrypt(f"BEACON:{NODE_ID}:{time.time()}".encode()) + public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        sendp(pkt, iface=iface, verbose=0, count=5)
        await asyncio.sleep(10)

# 🔹 Relais
async def relay_traffic():
    def handle_packet(pkt):
        if Raw in pkt and pkt[Dot11].addr1 == "ff:ff:ff:ff:ff:ff":
            try:
                pub_key_pem = pkt[Raw].load[-256:]
                pub_key = serialization.load_pem_public_key(pub_key_pem)
                pctamalou_decrypt(pkt[Raw].load[:-256], pub_key)  # Vérifie validité
                sendp(pkt, iface=iface, verbose=0)
            except Exception:
                pass  # Ignore paquets invalides
    sniff(iface=iface, prn=handle_packet, store=0)

if __name__ == "__main__":
    print("🔥 PCTAMALOU NODE RUNNER – AIRNET 🔥")
    print("Starting node setup...")
    try:
        setup_mesh()
    except Exception as e:
        print(f"Erreur setup : {e}. Vérifiez root (sudo) et matériel.")
        exit(1)
    print("Node is live! Relaying traffic and sending beacons...")
    asyncio.ensure_future(send_beacon())
    asyncio.ensure_future(relay_traffic())
    asyncio.get_event_loop().run_forever()
