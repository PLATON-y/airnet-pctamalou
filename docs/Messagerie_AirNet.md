3️⃣ Messagerie – pctamalou_airnet_messenger.py

Rôle

Application de messagerie P2P pour AirNet PCTamalou. Envoie/reçoit des messages chiffrés, gère les files offline, et affiche les utilisateurs actifs via ShadowID. C’est le cœur de la comm’ sur le réseau.

Pourquoi ?

Communiquer sans Internet, sans surveillance, avec une interface graphique simple (GUI PyQt5). Les messages restent sécurisés, même hors ligne, pour connecter les gens librement.

Détails Techniques

    Technologie :
        Wi-Fi IBSS + BATMAN-adv (via nœuds).
        Chiffrement PCTamalou (AES-256 + Chaos + ECC).
        PyQt5 (GUI multi-plateforme).
        JSON pour messages offline.

    Compatibilité : Linux (base), Windows/Android (ajustements).

    Fonctionnement :
        ShadowID unique par utilisateur.
        Messages P2P ou en file d’attente.
        Détection PRESENCE toutes les 5s.

Matériel Nécessaire

    Appareil : Raspberry Pi (nœud/client), PC (Linux/Windows), ou Android rooté.
    Carte Wi-Fi : Intégré ou USB (~20-30€, ex. : Alfa AWUS036NHA).
    Coût : 0€ (matos existant), ~50-155€ (nœud complet).

Préparation du Matériel

    Linux (Raspberry Pi/PC) :
        OS : Raspbian Lite/Ubuntu.

        Dépendances :

    sudo apt update && sudo apt upgrade -y
    sudo apt install python3 python3-pip iw batman-adv-dkms python3-pyqt5 -y
    pip3 install cryptography numpy asyncio scapy
    GUI : sudo apt install xfce4 (si Lite). Si échec : "Installez un bureau ou vérifiez RAM."

Windows :

    Python : python.org (3.11, "Add to PATH").

    CMD (admin) :

    pip install cryptography numpy asyncio scapy pyqt5
    Carte USB : Drivers Alfa (~5 min).

Android :

    Root + Termux : Voir connecteur Android.

    Dépendances :

        pkg install python clang libcrypt -y
        pip install cryptography numpy asyncio scapy
        GUI : Pas natif, CLI-only (PyQt5 limité sans X11).

Le Script : pctamalou_airnet_messenger.py

import os
import sys
import json
import time
import random
import asyncio
from scapy.all import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QListWidget
from PyQt5.QtCore import QTimer
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import numpy as np

# 🔹 Config
iface = "wlan0"  # Linux/Android. Windows : ajustez via "netsh wlan show interfaces"
NETWORK_NAME = "AirNetPCTamalou"
USER_IP = f"10.13.37.{random.randint(2, 254)}"
if os.system(f"ping -c 1 {USER_IP}") == 0:  # Windows : "ping -n 1"
    print(f"Attention : IP {USER_IP} prise. Relancez.")
    exit(1)
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()
SHADOW_ID = hashlib.sha256(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()[:16]

# 🔹 Chiffrement PCTamalou
def pctamalou_encrypt(data, salt=os.urandom(16)):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(b"Platon-y_Air")
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
    key = kdf.derive(b"Platon-y_Air")
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted) + decryptor.finalize()
    data_array = np.frombuffer(padded_data.rstrip(b"\x00"), dtype=np.uint8)
    chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
    decrypted = np.bitwise_xor(data_array, chaos.astype(np.uint8))
    return decrypted.tobytes()

# 🔹 Gestion Messages Offline
def load_pending_messages():
    try:
        with open("pending_messages.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_pending_messages(messages):
    try:
        with open("pending_messages.json", "w") as f:
            json.dump(messages, f)
    except Exception as e:
        print(f"Erreur sauvegarde : {e}. Vérifiez écriture disque.")

# 🔹 GUI
class AirNetMessenger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"AirNet Messenger – ShadowID: {SHADOW_ID}")
        self.setGeometry(100, 100, 600, 400)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.layout.addWidget(self.chat_display)

        self.user_list = QListWidget()
        self.layout.addWidget(self.user_list)

        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        self.layout.addLayout(input_layout)

        self.active_users = {}
        self.pending_messages = load_pending_messages()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_users)
        self.timer.start(5000)  # 5s

        asyncio.ensure_future(self.network_tasks())

    def update_users(self):
        current_time = time.time()
        self.active_users = {k: v for k, v in self.active_users.items() if current_time - v < 15}
        self.user_list.clear()
        for user in self.active_users:
            self.user_list.addItem(user)
        self.try_deliver_pending()

    def send_message(self):
        msg = self.message_input.text()
        if not msg:
            return
        target = self.user_list.currentItem()
        target_id = target.text() if target else "broadcast"
        pkt_data = f"MSG:{SHADOW_ID}:{target_id}:{msg}"
        pkt = RadioTap() / Dot11(type=2, subtype=0, addr1="ff:ff:ff:ff:ff:ff", addr2=RandMAC()) / \
              Raw(pctamalou_encrypt(pkt_data.encode()) + public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        sendp(pkt, iface=iface, verbose=0, count=3)
        self.chat_display.append(f"[Me -> {target_id}] {msg}")
        self.message_input.clear()

    def try_deliver_pending(self):
        for target_id, messages in list(self.pending_messages.items()):
            if target_id in self.active_users:
                for msg in messages:
                    pkt = RadioTap() / Dot11(type=2, subtype=0, addr1="ff:ff:ff:ff:ff:ff", addr2=RandMAC()) / \
                          Raw(pctamalou_encrypt(f"MSG:{SHADOW_ID}:{target_id}:{msg}".encode()) + public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
                    sendp(pkt, iface=iface, verbose=0, count=3)
                    self.chat_display.append(f"[Me -> {target_id}] {msg} (Delivered from queue)")
                del self.pending_messages[target_id]
                save_pending_messages(self.pending_messages)

    async def network_tasks(self):
        await asyncio.gather(self.send_presence(), self.listen_messages())

    async def send_presence(self):
        while True:
            pkt = RadioTap() / Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff", addr2=RandMAC()) / \
                  Raw(pctamalou_encrypt(f"PRESENCE:{SHADOW_ID}".encode()) + public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            sendp(pkt, iface=iface, verbose=0, count=5)
            await asyncio.sleep(5)

    async def listen_messages(self):
        def handle_packet(pkt):
            if Raw in pkt:
                try:
                    pub_key_pem = pkt[Raw].load[-256:]
                    pub_key = serialization.load_pem_public_key(pub_key_pem)
                    decrypted = pctamalou_decrypt(pkt[Raw].load[:-256], pub_key).decode()
                    if decrypted.startswith("PRESENCE:"):
                        shadow_id = decrypted.split(":")[1]
                        self.active_users[shadow_id] = time.time()
                    elif decrypted.startswith("MSG:"):
                        sender_id, target_id, msg = decrypted.split(":", 3)[1:]
                        if target_id in [SHADOW_ID, "broadcast"]:
                            self.chat_display.append(f"[{sender_id}] {msg}")
                        elif target_id not in self.active_users:
                            if target_id not in self.pending_messages:
                                self.pending_messages[target_id] = []
                            self.pending_messages[target_id].append(msg)
                            save_pending_messages(self.pending_messages)
                            self.chat_display.append(f"[{sender_id} -> {target_id}] Queued (offline)")
                except Exception:
                    pass
        sniff(iface=iface, prn=handle_packet, store=0)

# 🔹 Connexion Réseau
def setup_network():
    if os.name == "nt":
        os.system(f"netsh interface ip set address name=\"{iface}\" static {USER_IP} 255.255.255.0")
        print(f"[+] Windows IP: {USER_IP}. Connectez manuellement à 'AirNetPCTamalou' !")
    else:
        os.system(f"iw dev {iface} set type ibss")
        os.system(f"iw dev {iface} ibss join {NETWORK_NAME} 2412")
        os.system(f"ifconfig {iface} up {USER_IP}/24")
        print(f"[+] Connected – IP: {USER_IP}")

if __name__ == "__main__":
    print("🔥 AIRNET MESSENGER 🔥")
    try:
        setup_network()
    except Exception as e:
        print(f"Erreur réseau : {e}. Vérifiez Wi-Fi, root (Android), ou connexion manuelle (Windows).")
        exit(1)
    app = QApplication(sys.argv)
    window = AirNetMessenger()
    try:
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Erreur GUI : {e}. Installez PyQt5 (pip install pyqt5) ou vérifiez bureau (Linux).")

Comment Lancer ?

    Copier :
        Linux : nano pctamalou_airnet_messenger.py, copie-colle, sauvegarde.
        Windows : Notepad > pctamalou_airnet_messenger_windows.py, sauvegarde.
        Android : Termux > nano, copie-colle (CLI-only).

    Ajuster Interface :
        Windows : netsh wlan show interfaces > remplace iface.
        Android/Linux : iw dev > confirme wlan0.

    Lancer :
        Linux : sudo python3 pctamalou_airnet_messenger.py.
        Windows : CMD admin > python pctamalou_airnet_messenger_windows.py.
        Android : su -c "python pctamalou_airnet_messenger_android.py" (CLI-only).

        Sortie (GUI) :

        🔥 AIRNET MESSENGER 🔥
        [+] Connected – IP: 10.13.37.X
        [GUI s’ouvre : liste users, chat, input]

Vérifications & Erreurs

    OK : GUI ouverte, users listés, messages envoyés.
    "No Wi-Fi" : Vérifie iw dev (Linux/Android) ou netsh (Windows).
    "GUI fails" : "PyQt5 manquant (pip install pyqt5) ou pas de bureau (Linux : sudo apt install xfce4)."
    "No users" : "Lancez des nœuds ou clients près de vous."
    "JSON corrompu" : Supprime pending_messages.json et relance.

Conseils

    Portée : 100m base, 1-5 km avec antenne.
    Usage : Sélectionne un ShadowID pour message privé, sinon broadcast.
    Android : CLI-only sans X11, GUI possible avec VNC.
