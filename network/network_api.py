import json
import queue
import socket
import subprocess
import threading


SEQUENCED_TYPES = {"STATE_UPDATE"}


class NetworkBridge:
    """
    Bridge Python <-> proxy C.
    IPC Python Layer
    The C proxy listens on TCP localhost for Python, then forwards messages to
    other proxies over UDP. Python only talks to this local TCP socket.
    """

    def __init__(self, peer_id="peer_local", host="127.0.0.1", port=5000, auto_start=False, proxy_cmd=None):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self._my_ip = host
        self.security_manager = None
        self.auto_start = auto_start
        self.proxy_cmd = proxy_cmd
        self.proxy_process = None
        self.sock = None
        self.is_connected = False
        self.incoming_queue = queue.Queue()
        self.receive_thread = None
        self._seq_out = 0
        self._seq_in = {}
        self._entity_owners = {}
        self._entity_versions = {}

    def connect(self):
        if self.auto_start and self.proxy_process is None and self.proxy_cmd:
            self.proxy_process = subprocess.Popen(self.proxy_cmd)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.is_connected = True

        self.receive_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.receive_thread.start()

        print(f"[NetworkBridge] Connected to C proxy at {self.host}:{self.port}")
        return True

    def _listen_loop(self):
        buffer = ""
        while self.is_connected:
            try:
                data = self.sock.recv(4096)
                if not data:
                    self.is_connected = False
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        print(f"[NetworkBridge] Invalid JSON ignored: {line}")
                        continue

                    if self._is_new_message(msg):
                        self.incoming_queue.put(msg)

            except OSError:
                break
            except Exception as exc:
                if self.is_connected:
                    print(f"[NetworkBridge] Receive error: {exc}")
                break

        self.is_connected = False
        print("[NetworkBridge] Disconnected from C proxy")

    def _is_new_message(self, msg):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})
        seq = payload.get("seq")

        if msg_type not in SEQUENCED_TYPES or seq is None:
            return True

        sender = msg.get("sender_id") or msg.get("sender_peer_id") or ""
        key = (sender, msg_type)
        last_seq = self._seq_in.get(key, -1)

        if seq <= last_seq:
            return False

        self._seq_in[key] = seq
        return True

    def send_message(self, msg_type, target_peer_id="", payload=None, **kwargs):
        if not self.is_connected:
            print("[NetworkBridge] Not connected")
            return False

        peer_id = kwargs.get("peer_id")
        if isinstance(peer_id, str) and peer_id:
            target_peer_id = peer_id

        # - send_message("TYPE", {"k": "v"})
        # - send_message("TYPE", target_peer_id="peer_2", payload={...})
        # - send_message("TYPE", "peer_2", {...})
        if isinstance(target_peer_id, dict) and payload is None:
            payload = target_peer_id
            target_peer_id = ""

        if target_peer_id is None:
            target_peer_id = ""

        if not isinstance(target_peer_id, str):
            print("[NetworkBridge] target_peer_id must be a string")
            return False

        if payload is None:
            payload = {}
        elif not isinstance(payload, dict):
            print("[NetworkBridge] payload must be a dict")
            return False

        message = {
            "type": msg_type,
            "sender_id": self.peer_id,
            "target_peer_id": target_peer_id,
            "payload": payload,
        }

        try:
            data = json.dumps(message, separators=(",", ":")) + "\n"
            self.sock.sendall(data.encode("utf-8"))
            return True
        except Exception as exc:
            print(f"[NetworkBridge] Send error: {exc}")
            self.is_connected = False
            return False

    def join(self):
        return self.send_message("JOIN", "", {"peer_id": self.peer_id})

    def broadcast(self, event_type, data):
        return self.send_message("BROADCAST", "", {
            "event_type": event_type,
            "data": data,
        })

    def send_to(self, event_type, target_peer_id="", data=None):
        return self.send_message("SEND_TO", target_peer_id or "", {
            "event_type": event_type,
            "data": data,
        })

    def send_state_update(self, state):
        self._seq_out += 1
        return self.send_message("STATE_UPDATE", "", {
            "seq": self._seq_out,
            "state": state,
        })

    def request_ownership(self, target_peer_id, entity_id, reason=""):
        return self.send_message("OWNERSHIP_REQUEST", target_peer_id, {
            "entity_id": entity_id,
            "reason": reason,
        })

    def transfer_ownership(self, target_peer_id, entity_id, entity_state):
        return self.send_message("OWNERSHIP_TRANSFER", target_peer_id, {
            "entity_id": entity_id,
            "new_owner_id": target_peer_id,
            "state": entity_state,
        })

    def deny_ownership(self, target_peer_id, entity_id, reason=""):
        return self.send_message("OWNERSHIP_DENIED", target_peer_id, {
            "entity_id": entity_id,
            "reason": reason,
        })

    def return_ownership(self, target_peer_id, entity_id, entity_state):
        return self.send_message("OWNERSHIP_RETURN", target_peer_id, {
            "entity_id": entity_id,
            "state": entity_state,
        })
    
    def ping(self, target_peer_id=""):
        return self.send_message("PING", target_peer_id, {})
    
    def pong(self, target_peer_id=""):
        return self.send_message("PONG", target_peer_id, {})
    
    def shutdown(self):
        return self.send_message("SHUTDOWN", "", {})
    
    def get_updates(self):
        messages = []
        while not self.incoming_queue.empty():
            messages.append(self.incoming_queue.get())
        return messages

    def apply_updates(self, game):
        for msg in self.get_updates():
            self.apply_update(game, msg)

    def apply_update(self, game, msg):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "STATE_UPDATE":
            state = payload.get("state", payload)
            if hasattr(game, "apply_remote_state"):
                game.apply_remote_state(state)
            return

        if msg_type in {"BROADCAST", "SEND_TO", "REMOTE_EVENT"}:
            event_type = payload.get("event_type")
            data = payload.get("data", payload)
            if hasattr(game, "handle_remote_event"):
                game.handle_remote_event(event_type, data, msg)
            return

        if msg_type == "OWNERSHIP_REQUEST" and hasattr(game, "handle_ownership_request"):
            game.handle_ownership_request(msg)
        elif msg_type == "OWNERSHIP_TRANSFER" and hasattr(game, "handle_ownership_transfer"):
            game.handle_ownership_transfer(msg)
        elif msg_type == "OWNERSHIP_DENIED" and hasattr(game, "handle_ownership_denied"):
            game.handle_ownership_denied(msg)
        elif msg_type == "OWNERSHIP_RETURN" and hasattr(game, "handle_ownership_return"):
            game.handle_ownership_return(msg)

    def disconnect(self):
        self.is_connected = False

        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

        if self.proxy_process is not None:
            self.proxy_process.terminate()
            self.proxy_process = None

    # ---- Compatibility helpers used by Online mode ----
    def register_entity_owner(self, entity_id, owner_peer_id, ownership_version=0):
        if not entity_id or not owner_peer_id:
            return
        local_version = self._entity_versions.get(entity_id, -1)
        if ownership_version < local_version:
            return
        self._entity_owners[entity_id] = owner_peer_id
        self._entity_versions[entity_id] = ownership_version

    def get_entity_owner(self, entity_id):
        return self._entity_owners.get(entity_id)

    def get_ownership_version(self, entity_id):
        return self._entity_versions.get(entity_id, 0)

    def owns_entity(self, entity_id):
        return self.get_entity_owner(entity_id) == self.peer_id
