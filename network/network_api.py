import socket
import json
import threading
import queue

class NetworkBridge:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.sock = None
        self.is_connected = False
        
        # File d'attente thread-safe
        # Permet de séparer le thread réseau et la boucle principale du jeu (ex: Pygame)
        self.incoming_queue = queue.Queue()
        self.receive_thread = None

    def connect(self):
        """Se connecter au proxy C (processus en écoute sur le port 5000)"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
            self.is_connected = True
            print("[NetworkBridge] Connexion réussie au proxy C !")
            
            # Lancer un thread en arrière-plan pour écouter en continu
            self.receive_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.receive_thread.start()
            return True
        except ConnectionRefusedError:
            print("[NetworkBridge] ERREUR : Proxy C introuvable. Vérifiez qu'il est bien lancé !")
            return False

    def _listen_loop(self):
        """Thread en arrière-plan : reçoit les messages JSON et les place dans la file"""
        buffer = ""

        while self.is_connected:
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("[NetworkBridge] Le proxy C a fermé la connexion.")
                    self.is_connected = False
                    break
                
                buffer += data.decode('utf-8')

                # Gestion basique des messages concaténés (TCP)
                while True:
                    try:
                        msg_dict, index = json.JSONDecoder().raw_decode(buffer)
                        self.incoming_queue.put(msg_dict)
                        buffer = buffer[index:].lstrip()
                    except json.JSONDecodeError:
                        break

            except Exception as e:
                print(f"[NetworkBridge] Erreur dans le thread de réception : {e}")
                self.is_connected = False
                break

    def send_message(self, msg_type, payload_dict=None):
        """
        API pour le jeu : envoyer des données au réseau.
        - msg_type : type de message (ex: "REQUEST_OWNERSHIP")
        - payload_dict : état du jeu (ex: résultat de to_dict())
        """
        if not self.is_connected:
            print("[NetworkBridge] Impossible d'envoyer : non connecté.")
            return False

        if payload_dict is None:
            payload_dict = {}

        # Structure standard du message
        full_message = {
            "type": msg_type,
            "payload": payload_dict
        }

        try:
            json_data = json.dumps(full_message)
            self.sock.sendall(json_data.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[NetworkBridge] Erreur lors de l'envoi : {e}")
            self.is_connected = False
            return False

    def get_updates(self):
        """
        API pour la boucle de jeu.
        Retourne une liste de messages reçus sans bloquer l'exécution.
        """
        updates = []
        while not self.incoming_queue.empty():
            updates.append(self.incoming_queue.get())
        return updates

    def disconnect(self):
        """Fermer la connexion proprement"""
        self.is_connected = False
        if self.sock:
            self.sock.close()