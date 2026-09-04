# DEPRECATED: legacy prototype — use the airnet package (Phase 1+) instead of this script.
import os
import time
import random
import asyncio
import argparse
import pyaudio
from scapy.all import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QComboBox, QLabel
from PyQt5.QtCore import QTimer
from cryptography.hazmat.primitives import hashes, ciphers, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ec
import numpy as np
import sys

# 🔹 Config
iface = "wlan0"  # À ajuster (Windows: "Wi-Fi", Android: rooté)
NETWORK_NAME = "AirNetPCTamalou"
USER_IP = f"10.13.37.{random.randint(2, 254)}"
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()
SHADOW_ID = hashlib.sha256(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()[:16]

# 🔹 Chiffrement PCTamalou
def pctamalou_encrypt(data, salt=os.urandom(16)):
    kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, 100000)
    key = kdf.derive(b"Platon-y_Air")
    data_array = np.frombuffer(data, dtype=np.uint8)
    chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
    chaotic_data = np.bitwise_xor(data_array, chaos.astype(np.uint8))
    iv = os.urandom(16)
    cipher = ciphers.Cipher(ciphers.algorithms.AES(key), ciphers.modes.CBC(iv))
    encryptor = cipher.encryptor()
    padded = chaotic_data.tobytes() + b"\x00" * (16 - len(chaotic_data) % 16)
    encrypted = encryptor.update(padded) + encryptor.finalize()
    signature = private_key.sign(encrypted, ec.ECDSA(hashes.SHA256()))
    return salt + iv + encrypted + signature

def pctamalou_decrypt(ciphertext, sender_public_key):
    salt, iv, encrypted, signature = ciphertext[:16], ciphertext[16:32], ciphertext[32:-64], ciphertext[-64:]
    sender_public_key.verify(signature, encrypted, ec.ECDSA(hashes.SHA256()))
    kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, 100000)
    key = kdf.derive(b"Platon-y_Air")
    cipher = ciphers.Cipher(ciphers.algorithms.AES(key), ciphers.modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(encrypted) + decryptor.finalize()
    data_array = np.frombuffer(padded.rstrip(b"\x00"), dtype=np.uint8)
    chaos = np.sin(np.arange(len(data_array)) * 0.13) * 255
    return np.bitwise_xor(data_array, chaos.astype(np.uint8)).tobytes()

# 🔹 Audio Config (Qualité ajustable)
QUALITY_OPTIONS = {
    "low": (8000, 512),   # 8kHz, 512 frames (~64ms)
    "med": (16000, 1024), # 16kHz, 1024 frames (~64ms)
    "high": (44100, 1024) # 44.1kHz, 1024 frames (~23ms)
}

# 🔹 Audio
def init_audio(quality="med"):
    rate, chunk = QUALITY_OPTIONS[quality]
    p = pyaudio.PyAudio()
    stream_in = p.open(format=pyaudio.paInt16, channels=1, rate=rate, input=True, frames_per_buffer=chunk)
    stream_out = p.open(format=pyaudio.paInt16, channels=1, rate=rate, output=True, frames_per_buffer=chunk)
    return p, stream_in, stream_out, chunk

# 🔹 Réseau
def setup_network():
    if os.name == "nt":
        os.system(f"netsh interface ip set address name=\"{iface}\" static {USER_IP} 255.255.255.0")
    else:
        os.system(f"iw dev {iface} set type ibss")
        os.system(f"iw dev {iface} ibss join {NETWORK_NAME} 2412")
        os.system(f"ifconfig {iface} up {USER_IP}/24")
    print(f"[+] Connected – IP: {USER_IP} – ShadowID: {SHADOW_ID}")

def send_voice_packet(target_id, audio_data):
    pkt_data = f"VOICE:{SHADOW_ID}:{target_id}".encode() + audio_data
    pkt = RadioTap() / Dot11(type=2, subtype=0, addr1="ff:ff:ff:ff:ff:ff", addr2=RandMAC()) / \
          Raw(pctamalou_encrypt(pkt_data) + public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    sendp(pkt, iface=iface, verbose=0)

# 🔹 Détection Nœuds Actifs
active_nodes = {}

async def detect_nodes():
    def handle_packet(pkt):
        if Raw in pkt and pkt[Dot11].type == 0 and pkt[Dot11].subtype == 8:  # Beacon
            try:
                pub_key_pem = pkt[Raw].load[-256:]
                pub_key = serialization.load_pem_public_key(pub_key_pem)
                decrypted = pctamalou_decrypt(pkt[Raw].load[:-256], pub_key).decode()
                if decrypted.startswith("BEACON:"):
                    node_id = decrypted.split(":")[1]
                    active_nodes[node_id] = time.time()
            except Exception:
                pass
    sniff(iface=iface, prn=handle_packet, store=0, timeout=10)
    current_time = time.time()
    active_nodes.update({k: v for k, v in active_nodes.items() if current_time - v < 30})
    return list(active_nodes.keys())

# 🔹 CLI
async def cli_call(target_id, quality="med"):
    p, stream_in, stream_out, chunk = init_audio(quality)
    print(f"🎙 Appel vers {target_id} – Qualité: {quality} – Parlez ! (Ctrl+C pour stopper)")
    asyncio.ensure_future(listen_voice_packets())
    try:
        while True:
            audio = stream_in.read(chunk)
            send_voice_packet(target_id, audio)
            await asyncio.sleep(chunk / QUALITY_OPTIONS[quality][0])  # Sync avec taux
    except KeyboardInterrupt:
        stream_in.stop_stream(); stream_in.close()
        stream_out.stop_stream(); stream_out.close()
        p.terminate()
        print("Appel terminé.")

async def listen_voice_packets():
    def handle_packet(pkt):
        if Raw in pkt and "VOICE:" in pkt[Raw].load.decode(errors="ignore"):
            try:
                pub_key_pem = pkt[Raw].load[-256:]
                pub_key = serialization.load_pem_public_key(pub_key_pem)
                decrypted = pctamalou_decrypt(pkt[Raw].load[:-256], pub_key)
                sender_id, target_id = decrypted.decode().split(":", 2)[1:3]
                audio_data = decrypted[len(f"VOICE:{sender_id}:{target_id}"):]
                if target_id == SHADOW_ID:
                    stream_out.write(audio_data)
                    print(f"[VOICE from {sender_id}]")
            except Exception:
                pass
    sniff(iface=iface, prn=handle_packet, store=0)

# 🔹 GUI
class AirNetVoiceGUI(QMainWindow):
    def __init__(self, quality="med"):
        super().__init__()
        self.setWindowTitle(f"AirNet Voice – ShadowID: {SHADOW_ID}")
        self.setGeometry(100, 100, 400, 200)
        self.quality = quality
        self.p, self.stream_in, self.stream_out, self.chunk = init_audio(quality)

        # Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.label = QLabel("Choisissez un nœud à appeler :")
        layout.addWidget(self.label)

        self.node_list = QComboBox()
        layout.addWidget(self.node_list)

        self.call_button = QPushButton("Appeler")
        self.call_button.clicked.connect(self.start_call)
        layout.addWidget(self.call_button)

        self.stop_button = QPushButton("Stopper")
        self.stop_button.clicked.connect(self.stop_call)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

        # Timer pour mise à jour des nœuds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_nodes)
        self.timer.start(5000)  # 5s

        asyncio.ensure_future(self.listen_voice_packets_gui())
        self.update_nodes()

    def update_nodes(self):
        nodes = asyncio.run(detect_nodes())
        self.node_list.clear()
        self.node_list.addItems(nodes)

    def start_call(self):
        self.target_id = self.node_list.currentText()
        if not self.target_id:
            self.label.setText("Aucun nœud sélectionné !")
            return
        self.call_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.label.setText(f"Appel vers {self.target_id} – Parlez !")
        asyncio.ensure_future(self.send_voice_loop())

    async def send_voice_loop(self):
        while self.call_button.isEnabled() == False:
            audio = self.stream_in.read(self.chunk)
            send_voice_packet(self.target_id, audio)
            await asyncio.sleep(self.chunk / QUALITY_OPTIONS[self.quality][0])

    def stop_call(self):
        self.call_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.label.setText("Appel terminé. Choisissez un nœud :")

    async def listen_voice_packets_gui(self):
        await listen_voice_packets()

    def closeEvent(self, event):
        self.stream_in.stop_stream(); self.stream_in.close()
        self.stream_out.stop_stream(); self.stream_out.close()
        self.p.terminate()
        event.accept()

# 🔹 Main
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AirNet Voice – Appels chiffrés")
    parser.add_argument("--mode", choices=["cli", "gui"], default="cli", help="Mode: CLI ou GUI")
    parser.add_argument("--quality", choices=["low", "med", "high"], default="med", help="Qualité audio")
    parser.add_argument("--target", help="ShadowID à appeler (CLI uniquement)")
    args = parser.parse_args()

    print("🔥 AIRNET VOICE – appels chiffrés 🔥")
    setup_network()

    if args.mode == "cli":
        nodes = asyncio.run(detect_nodes())
        print(f"Nœuds actifs : {nodes}")
        target_id = args.target if args.target else input("Entrez le ShadowID à appeler : ")
        if target_id not in nodes and target_id:
            print("Nœud non trouvé !")
            sys.exit(1)
        asyncio.run(cli_call(target_id, args.quality))
    else:
        try:
            app = QApplication(sys.argv)
            window = AirNetVoiceGUI(args.quality)
            window.show()
            sys.exit(app.exec_())
        except Exception as e:
            print(f"GUI foiré : {e}. Passe en CLI avec --mode cli !")
            sys.exit(1)
