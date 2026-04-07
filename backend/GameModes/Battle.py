import json
import os
from pathlib import Path
from backend.GameModes.GameMode import GameMode
from backend.Utils.class_by_name import general_from_name
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Pikeman import Pikeman
from backend.Class.Units.Crossbowman import Crossbowman


class Battle(GameMode):

    def __init__(self):
        super().__init__()
        self.max_tick = None
        self.tick = 0
        self.tick_delay = 1.0  # seconds between simulation ticks
        self.frame_delay = 0.05  # sleep duration when not using pygame
        self.verbose = True

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

    def launch(self):
        self.affichage.initialiser()

    def gameLoop(self):
        import time
        use_pygame = getattr(self.affichage, "uses_pygame", False)
        clock = None
        if use_pygame:
            import pygame
            clock = pygame.time.Clock()
        else:
            pygame = None  # placeholder for cleanup branch

        # Set battle instance in affichage for save/load (works for both Pygame and Terminal)
        if hasattr(self.affichage, 'set_battle_instance'):
            self.affichage.set_battle_instance(self)
        
        # Initial display (helps fill buffers for curses/pygame alike)
        self.affichage.afficher(self.map, army1=self.army1, army2=self.army2)
        running = True
        last_tick_time = time.time()
        base_tick_delay = getattr(self, "tick_delay", 1.0)
        tick_delay = base_tick_delay
        frame_delay = getattr(self, "frame_delay", 0.05)

        while running:
            # Check if battle should continue
            battle_continues = (
                not self.army1.isEmpty() and 
                not self.army2.isEmpty() and 
                (self.max_tick is None or self.tick < self.max_tick)
            )
            paused = False
            if hasattr(self.affichage, "is_paused") and callable(getattr(self.affichage, "is_paused")):
                try:
                    paused = self.affichage.is_paused()
                except Exception:
                    paused = False

            if battle_continues and not paused:
                # Get speed multiplier from display (if available)
                if hasattr(self.affichage, 'battle_speed_multiplier'):
                    speed_mult = self.affichage.battle_speed_multiplier
                    tick_delay = base_tick_delay * speed_mult
                else:
                    tick_delay = base_tick_delay
                
                # Check if enough time has passed for next tick
                current_time = time.time()
                if current_time - last_tick_time >= tick_delay:
                    # Store previous positions for smooth animation (before battle tick)
                    if hasattr(self.affichage, 'unit_previous_positions'):
                        for unit in self.army1.living_units() + self.army2.living_units():
                            if unit.position is not None:
                                self.affichage.unit_previous_positions[unit.id] = unit.position

                    # Execute one battle tick
                    self.army1.fight(self.map, otherArmy=self.army2)
                    self.army2.fight(self.map, otherArmy=self.army1)
                    self.save()
                    self.tick += 1
                    last_tick_time = current_time
                    
                    if getattr(self, "verbose", True):
                        army1_count = len(self.army1.living_units())
                        army2_count = len(self.army2.living_units())
                        #print(f"Tick {self.tick}: Army1={army1_count} units, Army2={army2_count} units")
            
            # Update display (this will handle input and events internally)
            result = self.affichage.afficher(self.map, army1=self.army1, army2=self.army2)
            
            # If afficher returns "QUIT", user wants to quit
            if result == "QUIT":
                running = False
                break
            elif result == "LOAD":
                # Quick load requested
                if hasattr(self.affichage, '_quick_load'):
                    # Get selected filename from menu
                    save_files = self.affichage._get_save_files()
                    selected_filename = None
                    if save_files and hasattr(self.affichage, 'load_menu_selected_index'):
                        if 0 <= self.affichage.load_menu_selected_index < len(save_files):
                            selected_filename = save_files[self.affichage.load_menu_selected_index]
                    
                    loaded_battle = self.affichage._quick_load(selected_filename)
                    if loaded_battle:
                        # Replace current battle with loaded one
                        self.tick = loaded_battle.tick
                        self.max_tick = loaded_battle.max_tick
                        self.army1 = loaded_battle.army1
                        self.army2 = loaded_battle.army2
                        self.map = loaded_battle.map
                        # Update references
                        self.army1.gameMode = self
                        self.army2.gameMode = self
                        self.map.gameMode = self
                        if hasattr(self.affichage, 'set_battle_instance'):
                            self.affichage.set_battle_instance(self)
                        print("Battle loaded successfully!")
                        last_tick_time = time.time()  # Reset tick timer

            # If battle is over, show final state but keep window open
            if not battle_continues:
                # Battle ended - show final results
                if getattr(self, "verbose", True):
                    if self.army1.isEmpty():
                        print("Battle Over: Army 2 wins!")
                    elif self.army2.isEmpty():
                        print("Battle Over: Army 1 wins!")
                    elif self.max_tick and self.tick >= self.max_tick:
                        print(f"Battle Over: Reached max tick ({self.max_tick})")
                        army1_count = len(self.army1.living_units())
                        army2_count = len(self.army2.living_units())
                        print(f"Final: Army1={army1_count} units, Army2={army2_count} units")
                if not getattr(self.affichage, "wait_for_close", True):
                    running = False
                    break

            if clock:
                clock.tick(60)
            else:
                if frame_delay > 0:
                    time.sleep(frame_delay)

        # Clean up pygame when exiting
        if pygame:
            pygame.quit()
        if getattr(self, "verbose", True):
            print("Battle ended. Exiting...")

    def save(self):
        pass
