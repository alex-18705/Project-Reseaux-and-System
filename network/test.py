import socket
import json
import threading
import queue
import time


class NetworkBridge:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.sock = None
        self.is_connected = False

        self.incoming_queue = queue.Queue()
        self.receive_thread = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
            self.is_connected = True
            print("[NetworkBridge] ✅ Connected to C Proxy")

            self.receive_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.receive_thread.start()
            return True
        except Exception as e:
            print("[NetworkBridge] ❌ Connection failed:", e)
            return False

    def _listen_loop(self):
        buffer = ""
        while self.is_connected:
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("[NetworkBridge] Disconnected from proxy")
                    self.is_connected = False
                    break

                buffer += data.decode()

                while True:
                    try:
                        msg, idx = json.JSONDecoder().raw_decode(buffer)
                        self.incoming_queue.put(msg)
                        buffer = buffer[idx:].lstrip()
                    except:
                        break

            except Exception as e:
                print("[NetworkBridge] Receive error:", e)
                self.is_connected = False
                break

    def send_message(self, msg_type, payload=None):
        if not self.is_connected:
            print("[NetworkBridge] Not connected!")
            return

        if payload is None:
            payload = {}

        msg = {
            "type": msg_type,
            "payload": payload
        }

        try:
            data = json.dumps(msg)
            self.sock.sendall(data.encode())
            print("[SENT]:", msg)
        except Exception as e:
            print("[NetworkBridge] Send error:", e)

    def get_updates(self):
        updates = []
        while not self.incoming_queue.empty():
            updates.append(self.incoming_queue.get())
        return updates


# ==========================
# MAIN TEST
# ==========================
if __name__ == "__main__":
    net = NetworkBridge()

    if not net.connect():
        exit()

    def sender_loop():
        count = 0
        while net.is_connected:
            msg = f"hello {count}"
            net.send_message("TEST", {"msg": msg})
            count += 1
            time.sleep(2)

    threading.Thread(target=sender_loop, daemon=True).start()

    while True:
        updates = net.get_updates()
        for msg in updates:
            print("[RECEIVED]:", msg)
        time.sleep(0.1)
