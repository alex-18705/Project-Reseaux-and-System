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

    def __init__(self, peer_id=None, py_port=5000):
        super().__init__()
        self.max_tick = None
        self.tick = 0
        self.tick_delay = 1.0  # seconds between simulation ticks
        self.frame_delay = 0.05  # sleep duration when not using pygame
        self.verbose = True
        self.my_army = None
        self.othersArmy = {} # {"id" : "army"}
        self.my_id = peer_id or str(uuid.uuid4())
        self.network_bridge = NetworkBridge(peer_id=self.my_id, port=py_port)
        self.know_ip= set()
        self._last_status_tick = -1
        self.army_colors = [
            (255, 50, 50),
            (50, 100, 255),
            (60, 200, 90),
            (240, 210, 60),
            (190, 90, 255),
            (255, 140, 60),
        ]

    def flat(self):
        new = Army()
        list_units = []
        for k in self.othersArmy.keys():
            new.gameMode = self.othersArmy[k].gameMode
            list_units.append(self.othersArmy[k].units)
        new.units = [u for sublist in list_units for u in sublist]
        return new

    def update_army(self,global_army):
        for k in self.othersArmy.keys():
            for u in list(self.othersArmy[k].units):
                if u not in global_army.units: self.othersArmy[k].units.remove(u)

    def get_display_armies(self):
        armies = [(self.my_id, self.my_army)]
        for peer_id in sorted(self.othersArmy.keys()):
            armies.append((peer_id, self.othersArmy[peer_id]))

        display_armies = []
        for index, (peer_id, army) in enumerate(armies):
            display_armies.append({
                "id": peer_id,
                "army": army,
                "color": self.army_colors[index % len(self.army_colors)],
            })
        return display_armies

    def continue_condition(self):
        return True

    def end(self):
        if hasattr(self.affichage, "shutdown"):
            self.affichage.shutdown()

    def message_recieve(self):
        return False

    def run(self):
        self.network_bridge.apply_updates(self)

        all_enemy_army = self.flat()
        if not all_enemy_army.living_units():
            if self.tick != self._last_status_tick and self.tick % 30 == 0:
                print(f"[Online] {self.my_id}: waiting for remote army...")
                self._last_status_tick = self.tick
            self.network_bridge.send_state_update(self.create_state_payload())
            self.tick += 1
            return

        for remote_army in self.othersArmy.values():
            if remote_army.general is not None:
                remote_army.fight(self.map, otherArmy=self.my_army)

        self.my_army.fight(self.map, otherArmy=all_enemy_army)
        self.update_army(all_enemy_army)

        self.network_bridge.send_state_update(self.create_state_payload())

        self.tick += 1

    def apply_remote_state(self, state):
        if not state:
            return
        peer_id = state.get("peer_id")
        army_data = state.get("army")
        if not peer_id or peer_id == self.my_id or not army_data:
            return
        if isinstance(army_data, str):
            army = json_to_army(army_data)
        else:
            army = json_to_army(json.dumps(army_data))
        army.gameMode = self
        for unit in army.units:
            unit.army = army
        if peer_id not in self.othersArmy:
            print(f"[Online] {self.my_id}: received remote army from {peer_id}")
        self.othersArmy[peer_id] = army

    def create_state_payload(self):
        return {
            "peer_id": self.my_id,
            "tick": self.tick,
            "army": army_to_dict(self.my_army)
        }

    def launch(self):
        self.affichage.initialiser()
        self.network_bridge.connect()
        self.network_bridge.join()

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
        army = {}
        for k in self.othersArmy.keys() :
            army[k] = army_to_json(self.othersArmy[k])
        army[self.my_id] = army_to_json(self.my_army)
        return str(army)

    @property
    def army1(self):
        return self.my_army

    @army1.setter
    def army1(self, value):
        value.gameMode = self
        self.my_army = value

    @property
    def army2(self):
        return self.flat()

    @army2.setter
    def army2(self, value):
        value.gameMode = self
        #self.othersArmy.append(value)

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
