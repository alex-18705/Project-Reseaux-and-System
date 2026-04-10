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
from network.network_api import NetworkBridge


# client1 envoie les ordres de sont général -> client2 execute les ordres et envoie l'état du monde -> client1


class Online(GameMode):

    def __init__(self):
        super().__init__()
        self.max_tick = None
        self.tick = 0
        self.tick_delay = 1.0  # seconds between simulation ticks
        self.frame_delay = 0.05  # sleep duration when not using pygame
        self.verbose = True
        self.my_army = None
        self.othersArmy = []
        self.computer_id = str(uuid.uuid4())
        self.network_bridge = NetworkBridge()

    @property
    def army1(self):
        return self.my_army

    @army1.setter
    def army1(self, value):
        value.gameMode = self
        self.my_army=value

    @property
    def army2(self):
        return self.othersArmy[0]

    @army2.setter
    def army2(self, value):
        value.gameMode = self
        self.othersArmy.append(value)

    def add_army(self,value):
        value.gameMode = self
        self.othersArmy.append(value)

    def remove_army(self,value):
        self.othersArmy.remove(value)

    def flat(self):
        new = Army()
        list_units = []
        for a in self.othersArmy:
            new.general = a.general
            new.gameMode = a.gameMode
            list_units.append(a.units)
        new.units = [u for sublist in list_units for u in sublist]
        return new

    def update_army(self,global_army):
        for a in self.othersArmy:
            for u in a.units:
                if u not in global_army.units: a.units.remove(u)




        
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
                "obstacles": [{"position": list(obs.position)} for obs in self.map.obstacles if hasattr(obs, 'position')]
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

    def end(self):
        if hasattr(self.affichage, "shutdown"):
            self.affichage.shutdown()

    def message_recieve(self):
        return False

    def run(self):
        messages = self.network_bridge.get_updates()


        all = self.flat()
        self.army1.fight(self.map, otherArmy=all)
        all.fight(self.map, otherArmy=self.army1)
        self.save()
        self.tick += 1

    def launch(self):
        self.affichage.initialiser()
        self.network_bridge.connect()

    def save(self):
        pass
