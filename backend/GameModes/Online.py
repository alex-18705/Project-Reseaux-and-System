import ast
import json
import os
import uuid
from pathlib import Path

from backend.Class.Army import Army
from backend.GameModes.GameMode import GameMode
from backend.Utils.class_by_name import general_from_name
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Pikeman import Pikeman
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Utils.network_ownership import initialize_ownership, get_ownership_manager
from backend.Utils.convert_json import json_to_army, army_to_json, army_to_dict, map_to_dict, json_to_map
from network.network_api import NetworkBridge


# client1 envoie les ordres de sont général -> client2 execute les ordres et envoie l'état du monde -> client1


class Online(GameMode):

    def __init__(self, py_port=5000, lan_port=6000, remote_port=6000, is_first=True, spawn_slot=None):
        super().__init__()
        self.max_tick = None
        self.tick = 0
        self.tick_delay = 1.0
        self.frame_delay = 0.05
        self.verbose = True
        self.my_army = None
        self.othersArmy = {} 
        self.network_bridge = NetworkBridge(port=py_port)
        self.know_ip= set()
        self.my_id = str(uuid.uuid4())
        self.lan_port = lan_port
        self.remote_port = remote_port
        self.is_first = is_first # Host is Blue (P1), Joiner is Red (P2)
        if spawn_slot is None:
            spawn_slot = 0 if is_first else max(1, lan_port - remote_port)
        self.spawn_slot = spawn_slot
        self.has_started = False
        self.current_sender_id = None
        
        # Initialize ownership system
        initialize_ownership(self.my_id)
        
        self._army_base_positions = {}
        self._army_mirrored_for_width = None
        self._last_known_remote_armies = 0
        self._last_logged_map_signature = None

    def _map_signature(self):
        if self.map is None:
            return "none"
        width = getattr(self.map, "width", "?")
        height = getattr(self.map, "height", "?")
        obstacles = len(getattr(self.map, "obstacles", []))
        return f"{width}x{height}, obstacles={obstacles}"

    def _log_map_if_changed(self):
        signature = self._map_signature()
        if signature != self._last_logged_map_signature:
            print(f"[Online] Map courante : {signature}")
            self._last_logged_map_signature = signature

    def _mark_army_owner(self, army, army_id):
        if army is None:
            return
        for unit in army.units:
            unit.network_owner_id = army_id

    def _remember_base_positions(self):
        if self.my_army is None:
            return
        self._army_base_positions = {
            unit.id: unit.position
            for unit in self.my_army.units
            if unit.position is not None
        }

    def _deploy_my_army_for_current_map(self):
        if self.my_army is None or self.map is None:
            return
        width = getattr(self.map, "width", None)
        height = getattr(self.map, "height", None)
        if width is None or height is None or self._army_mirrored_for_width == width:
            return
        print(f"[Online] Deploying army slot {self.spawn_slot} on map {width}x{height}...")
        y_offset = 0 if self.spawn_slot == 0 else self.spawn_slot * 20
        for unit in self.my_army.units:
            base_pos = self._army_base_positions.get(unit.id, unit.position)
            if base_pos:
                x, y = base_pos
                if self.spawn_slot != 0:
                    x = (width - 1) - x
                y = max(0, min(height - 1, y + y_offset))
                unit.position = (x, y)
        self._army_mirrored_for_width = width

    def flat(self):
        new = Army()
        all_units = []
        for army_id in self.othersArmy:
            all_units.extend(self.othersArmy[army_id].units)
        new.units = all_units
        return new

    def continue_condition(self):
        return self.max_tick is None or self.tick < self.max_tick

    def end(self):
        # Fermeture de l'affichage
        if hasattr(self.affichage, "shutdown"):
            self.affichage.shutdown()
        
        # Fermeture de la connexion réseau et du Proxy C
        if hasattr(self, "network_bridge"):
            print("[Online] Fermeture de la connexion réseau...")
            self.network_bridge.disconnect()

    def request_unit_ownership(self, unit_id: str):
        """Sends an OWNERSHIP_REQUEST to the current owner."""
        ownership = get_ownership_manager()
        current_owner = ownership.get_owner(unit_id)
        if current_owner and current_owner != self.my_id:
            ownership.request_ownership(unit_id, self.my_id)
            # Find the IP of the current_owner (we broadcast if we don't know it specifically)
            # For simplicity, we broadcast to all known IPs, the owner will process it.
            for ip in self.know_ip:
                self.network_bridge.send_message("OWNERSHIP_REQUEST", ip, {
                    "unit_id": unit_id,
                    "requester_id": self.my_id
                })

    def message_receive(self):
        """
        Recuperer les messages reseau, synchroniser la map envoyee par le host,
        puis mettre a jour les armees des autres joueurs.
        """
        messages = self.network_bridge.get_updates()
        updated = False
        ownership = get_ownership_manager()

        for msg in messages:
            sender_ip = msg.get("_sender_ip")
            if sender_ip and sender_ip not in self.know_ip:
                print(f"[Online] Nouveau pair decouvert : {sender_ip}")
                self.know_ip.add(sender_ip)

            msg_type = msg.get("type", "SYNC_UPDATE")
            payload = msg.get("payload", {})
            if not isinstance(payload, dict):
                continue
                
            if msg_type == "OWNERSHIP_REQUEST":
                unit_id = payload.get("unit_id")
                requester_id = payload.get("requester_id")
                if unit_id and requester_id:
                    ownership.request_ownership(unit_id, requester_id)
                    # Automatically grant ownership if we are the current owner (for demonstration)
                    if ownership.grant_ownership(unit_id, requester_id):
                        print(f"[Ownership] Accord de la propriete de {unit_id} a {requester_id}")
                        for ip in self.know_ip:
                            self.network_bridge.send_message("OWNERSHIP_GRANT", ip, {
                                "unit_id": unit_id,
                                "new_owner_id": requester_id
                            })
                continue
            elif msg_type == "OWNERSHIP_GRANT":
                unit_id = payload.get("unit_id")
                new_owner_id = payload.get("new_owner_id")
                if unit_id and new_owner_id:
                    print(f"[Ownership] Transfert de {unit_id} vers {new_owner_id} confirme")
                    ownership.handle_grant(unit_id, new_owner_id)
                continue

            if "map" in payload and payload["map"]:
                try:
                    self.map = json_to_map(payload["map"])
                    self._deploy_my_army_for_current_map()
                    self._log_map_if_changed()
                except Exception as e:
                    print(f"[Online] Erreur lors du chargement de la map : {e}")

            armies_payload = payload.get("armies", payload)
            if not isinstance(armies_payload, dict):
                continue

            for army_id, army_data in armies_payload.items():
                if army_id != self.my_id:
                    self.current_sender_id = army_id
                    ownership.register_peer(army_id)
                    try:
                        army = json_to_army(army_data)
                        self._mark_army_owner(army, army_id)
                        self.othersArmy[army_id] = army
                        
                        # Register ownership of remote units
                        for unit in army.units:
                            ownership.assign_ownership(unit.id, army_id)
                    except Exception as e:
                        print(f"[Online] Erreur lors du chargement de l'armee de {army_id} : {e}")
                    updated = True
                else:
                    self.my_army = json_to_army(army_data)
                    self._mark_army_owner(self.my_army, self.my_id)
        
        known_remote_armies = len(self.othersArmy)
        if known_remote_armies != self._last_known_remote_armies:
            print(f"[Online] Armees distantes connues : {known_remote_armies}")
            self._last_known_remote_armies = known_remote_armies
        return updated

    def run(self):
        """
        Étape principale de la simulation pour le mode Online :
        1. Recevoir les mises à jour des pairs
        2. Si aucun pair, attendre et afficher 'En attente...'
        3. Si pair trouvé, exécuter la simulation
        4. Diffuser l'état local aux pairs
        """
        self.message_receive()

        if not self.othersArmy:
            if self.tick % 100 == 0:
                print("En attente d'un autre joueur...")
            # Diffuser quand même notre présence pour que l'autre puisse nous trouver
            self._broadcast_state()
            return

        if not self.has_started:
            print("Joueur rejoint ! Début de la bataille.")
            self.has_started = True

        # Register our own units' ownership if not done
        ownership = get_ownership_manager()
        for unit in self.my_army.units:
            ownership.assign_ownership(unit.id, self.my_id)

        # Exécuter la logique de combat pour NOS unités
        # We need to fight AGAINST everyone else combined
        all_enemies = self.flat() 
        
        self.current_sender_id = self.my_id # We are the executor for our own units
        self.my_army.fight(self.map, otherArmy=all_enemies)
        self.update_dead(all_enemies)
        
        # Incrémenter le tick
        self.tick += 1
        
        self._broadcast_state()

    def _broadcast_state(self):
        payload = self.create_payload()
        if not self.know_ip:
            # Envoie un paquet bidon pour enregistrer le port Python auprès du proxy C
            self.network_bridge.send_message("SYNC_UPDATE", "0.0.0.0", payload)
            return
            
        # Broadcast to all known IPs
        for ip in self.know_ip:
            self.network_bridge.send_message("SYNC_UPDATE", ip, payload)

    def update_dead(self, all_enemies):
        for army in self.othersArmy.values():
            army.units = [u for u in army.units if u in all_enemies.units]

    @property
    def army1(self):
        return self.my_army

    @property
    def army2(self):
        return self.flat()

    def launch(self):
        self._remember_base_positions()
        self._deploy_my_army_for_current_map()
        self._log_map_if_changed()

        self.affichage.initialiser()
        remote_ip = list(self.know_ip)[0] if self.know_ip else None
        self.network_bridge.connect(remote_ip=remote_ip, lan_port=self.lan_port, remote_port=self.remote_port)
        
        # Envoyer immédiatement un premier paquet pour s'enregistrer auprès du proxy C
        self._broadcast_state()

    def save(self):
        pass

    def load_payload(self, json_payload):
        print("ef", json_payload)
        army = ast.literal_eval(json_payload)
        print(army)
        for k in army.keys():
            if k == self.my_id:
                self.my_army = json_to_army(army[k])
            else:
                self.othersArmy[k] = json_to_army(army[k])

    def create_payload(self):
        armies = {
            self.my_id: army_to_dict(self.my_army)
        }
        # In multi-peer mode, everyone should ideally know about everyone.
        # If we only send OUR army, a new peer joining P1 (host) might not see P2 if P2 doesn't know P3 yet.
        # So we broadcast all known armies.
        for army_id, army in self.othersArmy.items():
            armies[army_id] = army_to_dict(army)

        result = {"armies": armies}
        # Only host (is_first) decides the map to avoid conflicts
        if self.is_first and self.map is not None and (self.tick < 20 or self.tick % 50 == 0):
            result["map"] = map_to_dict(self.map)
        return result


    @army1.setter
    def army1(self, value):
        value.gameMode = self
        self.my_army = value
        self._mark_army_owner(self.my_army, self.my_id)

    @army2.setter
    def army2(self, value):
        value.gameMode = self

    def to_dict(self):
        """Serialize battle state to dictionary for saving."""
        # Serialize units with their IDs
        units_by_id = {}
        for unit in self.army1.units + self.army2.units:
            units_by_id[unit.id] = {
                "id": unit.id,
                "unit_type": unit.unit_type(),
                "hp": unit.hp,
                "position": list(unit.position) if unit.position else None,
                "cooldown": unit.cooldown,
                "army": "army1" if unit in self.army1.units else "army2"
            }

        # Serialize generals (including AI state)
        general1_state = {}
        general2_state = {}
        if self.army1.general:
            general1_state = {
                "class": self.army1.general.__class__.__name__,
                "state": self._serialize_general_state(self.army1.general)
            }
        if self.army2.general:
            general2_state = {
                "class": self.army2.general.__class__.__name__,
                "state": self._serialize_general_state(self.army2.general)
            }

        return {
            "tick": self.tick,
            "max_tick": self.max_tick,
            "map": {
                "width": self.map.width if hasattr(self.map, 'width') else 100,
                "height": self.map.height if hasattr(self.map, 'height') else 100,
                "obstacles": [{"position": list(obs.position)} for obs in self.map.obstacles if
                              hasattr(obs, 'position')]
            },
            "army1": self.army1.to_dict(),
            "army2": self.army2.to_dict(),
            "units": units_by_id,
            "general1": general1_state,
            "general2": general2_state
        }

    def _serialize_general_state(self, general):
        """Serialize general's AI state (state of mind, planning, etc.)."""
        state = {}
        # Save GeneralClever specific state
        if hasattr(general, '_is_deployed'):
            state['_is_deployed'] = general._is_deployed
        if hasattr(general, '_max_hp_cache'):
            state['_max_hp_cache'] = general._max_hp_cache
        if hasattr(general, '_deployment_threshold'):
            state['_deployment_threshold'] = general._deployment_threshold
        return state

    @classmethod
    def from_dict(cls, data):
        """Reconstruct Battle from dictionary."""
        battle = cls()
        battle.tick = data.get("tick", 0)
        battle.max_tick = data.get("max_tick", None)

        # Reconstruct map
        from backend.Class.Map import Map
        map_data = data.get("map", {})
        battle.map = Map(map_data.get("width", 100), map_data.get("height", 100))

        # Reconstruct units
        units_by_id = {}
        units_data = data.get("units", {})
        for unit_id, unit_data in units_data.items():
            unit_type = unit_data["unit_type"]
            position = tuple(unit_data["position"]) if unit_data.get("position") else None
            army_name = unit_data.get("army", "army1")

            if unit_type == "Knight":
                unit = Knight(position)
            elif unit_type == "Pikeman":
                unit = Pikeman(position)
            elif unit_type == "Crossbowman":
                unit = Crossbowman(position)
            else:
                continue

            # Restore unit ID (override the auto-generated one)
            unit._Unit__id = unit_id

            # Restore unit state
            unit.hp = unit_data.get("hp", unit.hp)
            unit.cooldown = unit_data.get("cooldown", 0)
            units_by_id[unit_id] = unit

        # Reconstruct armies
        from backend.Class.Army import Army
        army1_data = data.get("army1", {})
        army2_data = data.get("army2", {})

        battle.army1 = Army(army1_data.get("owner"))
        battle.army2 = Army(army2_data.get("owner"))

        for unit_id in army1_data.get("unit_ids", []):
            if unit_id in units_by_id:
                battle.army1.add_unit(units_by_id[unit_id])

        for unit_id in army2_data.get("unit_ids", []):
            if unit_id in units_by_id:
                battle.army2.add_unit(units_by_id[unit_id])

        # Reconstruct generals with AI state
        general1_data = data.get("general1", {})
        general2_data = data.get("general2", {})

        if general1_data:
            general1 = general_from_name(general1_data["class"])()
            battle._restore_general_state(general1, general1_data.get("state", {}))
            battle.army1.general = general1
            general1.army = battle.army1

        if general2_data:
            general2 = general_from_name(general2_data["class"])()
            battle._restore_general_state(general2, general2_data.get("state", {}))
            battle.army2.general = general2
            general2.army = battle.army2

        # Link armies and map to battle
        battle.army1.gameMode = battle
        battle.army2.gameMode = battle
        battle.map.gameMode = battle

        return battle

    def _restore_general_state(self, general, state):
        """Restore general's AI state."""
        if hasattr(general, '_is_deployed') and '_is_deployed' in state:
            general._is_deployed = state['_is_deployed']
        if hasattr(general, '_max_hp_cache') and '_max_hp_cache' in state:
            general._max_hp_cache = state['_max_hp_cache']
        if hasattr(general, '_deployment_threshold') and '_deployment_threshold' in state:
            general._deployment_threshold = state['_deployment_threshold']
