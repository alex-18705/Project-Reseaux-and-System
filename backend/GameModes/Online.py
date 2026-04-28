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
from backend.Utils.convert_json import json_to_army, army_to_json, army_to_dict
from network.network_api import NetworkBridge


# client1 envoie les ordres de sont général -> client2 execute les ordres et envoie l'état du monde -> client1


class Online(GameMode):

    def __init__(self, py_port=5000, lan_port=6000, remote_port=6000, is_first=True):
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
        self.has_started = False

    def flat(self):
        new = Army()
        all_units = []
        for army_id in self.othersArmy:
            all_units.extend(self.othersArmy[army_id].units)
        new.units = all_units
        return new

    def continue_condition(self):
        return True

    def end(self):
        # Fermeture de l'affichage
        if hasattr(self.affichage, "shutdown"):
            self.affichage.shutdown()
        
        # Fermeture de la connexion réseau et du Proxy C
        if hasattr(self, "network_bridge"):
            print("[Online] Fermeture de la connexion réseau...")
            self.network_bridge.disconnect()

    def message_receive(self):
        """
        Récupère les mises à jour du pont réseau et met à jour l'état des autres armées.
        Découvre également automatiquement les nouveaux pairs.
        """
        messages = self.network_bridge.get_updates()
        updated = False
        for msg in messages:
            # Découverte automatique : ajouter l'expéditeur à know_ip s'il n'y est pas déjà
            sender_ip = msg.get("_sender_ip")
            if sender_ip and sender_ip not in self.know_ip:
                print(f"[Online] Nouveau pair découvert : {sender_ip}")
                self.know_ip.add(sender_ip)

            # Le payload envoyé est un dictionnaire {id: army_data}
            payload = msg.get("payload", {})
            if isinstance(payload, dict):
                for army_id, army_data in payload.items():
                    if army_id != self.my_id:
                        # Utiliser le chargement basé sur le dictionnaire
                        try:
                            self.othersArmy[army_id] = json_to_army(army_data)
                        except Exception as e:
                            print(f"[Online] Erreur lors du chargement de l'armée de {army_id} : {e}")
                        updated = True
                    else :
                        self.my_army = json_to_army(army_data)
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

        # Exécuter la logique de combat pour NOS unités
        all_enemies = self.flat()
        self.my_army.fight(self.map, otherArmy=all_enemies)
        print(len(all_enemies.living_units()))
        self.update_dead(all_enemies)
        
        # Incrémenter le tick
        self.tick += 1
        
        self._broadcast_state()

    def _broadcast_state(self):
        payload = self.create_payload()
        for ip in self.know_ip:
            self.network_bridge.send_message("SYNC_UPDATE", ip, payload)

    def update_dead(self, all_enemies):
        for army in self.othersArmy.values():
            for u in range(army.units):
                if army.units[u] not in all_enemies.units:
                    del army.units[u]

    @property
    def army1(self):
        return self.my_army

    @property
    def army2(self):
        return self.flat()

    def launch(self):
        # If we are the joiner, mirror our units to the right immediately
        if not self.is_first and self.my_army:
            print("[Online] Mirroring army to the right side...")
            for unit in self.my_army.units:
                if unit.position:
                    new_x = (self.map.width - 1) - unit.position[0]
                    unit.position = (new_x, unit.position[1])

        self.affichage.initialiser()
        remote_ip = list(self.know_ip)[0] if self.know_ip else None
        self.network_bridge.connect(remote_ip=remote_ip, lan_port=self.lan_port, remote_port=self.remote_port)

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
        # Only send OUR army state to avoid redundant data
        result= self.othersArmy.copy()
        result[self.my_id] = self.my_army
        return result


    @army1.setter
    def army1(self, value):
        value.gameMode = self
        self.my_army = value

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