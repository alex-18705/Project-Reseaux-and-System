from abc import ABC, abstractmethod

from backend.Class.Army import Army
from backend.Class.Map import Map
from frontend.Affichage import Affichage


class GameMode(ABC) :
    def __init__(self):
        self.__army1 = None
        self.__army2 = None
        self.__affichage = None
        self.__map = None
        self.isSave = False

    @abstractmethod
    def launch(self):
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def continue_condition(self):
        pass

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
            battle_continues = self.continue_condition()
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
                    self.run()
                    last_tick_time = current_time

                    if getattr(self, "verbose", True):
                        army1_count = len(self.army1.living_units())
                        army2_count = len(self.army2.living_units())
                        # print(f"Tick {self.tick}: Army1={army1_count} units, Army2={army2_count} units")

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

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def end(self):
        pass

    @property
    def army1(self):
        pass

    @army1.setter
    def army1(self, value: Army):
        pass

    @property
    def army2(self):
        pass

    @army2.setter
    def army2(self, value: Army):
        pass

    @property
    def map(self):
        return self.__map

    @map.setter
    def map(self, value: Map):
        value.gameMode = self
        self.__map = value

    @property
    def affichage(self):
        return self.__affichage

    @affichage.setter
    def affichage(self, value: Affichage):
        value.gameMode = self
        self.__affichage = value
