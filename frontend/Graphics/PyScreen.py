import sys
import time
from time import sleep

import pygame

from backend.Class.Army import Army
from backend.Class.Map import Map
from backend.Class.Obstacles.Rocher import Rocher
from backend.Class.Units.Castle import Castle
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Units.Elephant import Elephant
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Monk import Monk
from backend.Class.Units.Pikeman import Pikeman
from frontend.Affichage import Affichage


class PyScreen(Affichage):

    def initialiser(self):
        # Initialisation de Pygame
        pygame.init()
        # Création de la fenêtre
        self.WIDTH, self.HEIGHT = 1280, 720
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Affichage d'une tile")
        # Chargement de l'image

        self.offset_x, self.offset_y = 0, 0
        self.zoom_factor = 20
        self.unit_scale_multiplier = 4.5  # Multiplier to make units bigger and more visible

        # Paramètres de la vue isométrique
        self.tile_size = 10  # Taille d'une tuile carrée

        # Charger l'image de la tuile PNG (image carrée)
        self.TILE_IMAGE = pygame.image.load(self.path + "tile.bmp").convert_alpha()

        self.KNIGHT_IMAGE = pygame.image.load(self.path + "knight.bmp").convert_alpha()
        self.PIKEMAN_IMAGE = pygame.image.load(self.path + "pikeman.bmp").convert_alpha()
        self.CROSSBOWMAN_IMAGE = pygame.image.load(self.path + "crossbowman.bmp").convert_alpha()
        self.ROCHER_IMAGE = pygame.image.load(self.path + "rocher.png")
        self.CASTLE_IMAGE = pygame.image.load(self.path + "castle.png")
        self.ELEPHANT_IMAGE = pygame.image.load(self.path + "elephant.png")
        self.MONK_IMAGE = pygame.image.load(self.path + "monk.png")

        # For smooth movement animation
        self.unit_previous_positions = {}  # unit_id -> (x, y) - position before animation
        self.unit_animation_start_pos = {}  # unit_id -> (x, y) - position animation starts from
        self.animation_start_time = {}  # unit_id -> start_time
        self.animation_duration = 1.15  # Short tween for smooth movement without pauses

        # Minimap and UI settings
        self.show_minimap = True  # Toggle with M key
        self.minimap_size = 200  # Size of minimap in pixels
        self.minimap_position = (self.WIDTH - self.minimap_size - 10, 10)  # Top-right corner

        # Army visualization toggles (F1-F4)
        self.show_army_stats = True  # F1: Toggle all army stats
        self.show_army1_details = True  # F2: Toggle army1 details
        self.show_army2_details = True  # F3: Toggle army2 details
        self.show_unit_counts = True  # F4: Toggle unit type counts

        # Battle speed control (Z/X keys)
        self.battle_speed_multiplier = 1.0  # 1.0 = normal speed, >1.0 = faster, <1.0 = slower

        # Pause control (Space key)
        self.is_paused_state = False

        # Save/Load control
        self.quick_save_filename = "quicksave.json"
        self.battle_instance = None  # Will be set by Battle gameLoop
        self.show_load_menu = False  # Show file selection menu
        self.load_menu_selected_index = 0  # Currently selected file index

        # Initialize font for text display
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        actual_tile_size = int(self.tile_size * self.zoom_factor) + 4
        base_tile = pygame.transform.scale(self.TILE_IMAGE, (actual_tile_size, actual_tile_size))
        
        self.TILE_LIGHT = base_tile.copy()
        self.TILE_LIGHT.fill((60, 180, 40), special_flags=pygame.BLEND_RGB_MULT)
        
        self.TILE_DARK = base_tile.copy()
        self.TILE_DARK.fill((45, 150, 30), special_flags=pygame.BLEND_RGB_MULT)

    def _get_interpolated_position(self, unit):
        """Get the interpolated position for smooth movement animation."""
        if unit.position is None:
            return None

        unit_id = unit.id
        current_pos = unit.position

        # Check if this unit has moved (position changed since last stored)
        if unit_id in self.unit_previous_positions:
            stored_pos = self.unit_previous_positions[unit_id]

            # If position changed, start new animation
            if stored_pos != current_pos:
                # Store the animation start position and time
                self.unit_animation_start_pos[unit_id] = stored_pos
                self.animation_start_time[unit_id] = time.time()
                self.unit_previous_positions[unit_id] = current_pos
                return stored_pos  # Start from previous position
            else:
                # Position hasn't changed, check if we're still animating
                if unit_id in self.animation_start_time and unit_id in self.unit_animation_start_pos:
                    elapsed = time.time() - self.animation_start_time[unit_id]
                    if elapsed < self.animation_duration:
                        # Interpolate between animation start position and current position
                        start_pos = self.unit_animation_start_pos[unit_id]
                        t = elapsed / self.animation_duration
                        # Use smooth easing function (ease-in-out)
                        t = t * t * (3.0 - 2.0 * t)  # Smoothstep
                        interp_x = start_pos[0] + (current_pos[0] - start_pos[0]) * t
                        interp_y = start_pos[1] + (current_pos[1] - start_pos[1]) * t
                        return (interp_x, interp_y)
                    else:
                        # Animation complete - clean up
                        if unit_id in self.animation_start_time:
                            del self.animation_start_time[unit_id]
                        if unit_id in self.unit_animation_start_pos:
                            del self.unit_animation_start_pos[unit_id]

        # No previous position or animation complete - use current position
        if unit_id not in self.unit_previous_positions:
            self.unit_previous_positions[unit_id] = current_pos
        return current_pos

    def _get_max_hp(self, unit):
        """Get the maximum HP for a unit based on its type."""
        return unit.max_hp # Fallback to current HP if unknown type

    def _draw_hp_bar(self, unit, iso_x, iso_y, unit_size):
        """Draw HP bar above a unit."""
        max_hp = self._get_max_hp(unit)
        current_hp = max(0, unit.hp)  # Ensure non-negative
        hp_percentage = current_hp / max_hp if max_hp > 0 else 0

        # HP bar dimensions
        bar_width = unit_size
        bar_height = 4
        bar_x = int(iso_x - bar_width // 2)
        bar_y = int(iso_y - unit_size // 2 - 10)  # Position above unit

        # Draw background (black/dark)
        pygame.draw.rect(self.screen, (40, 40, 40),
                         (bar_x, bar_y, bar_width, bar_height))

        # Draw HP bar (green to red gradient based on HP)
        if hp_percentage > 0:
            hp_width = int(bar_width * hp_percentage)

            # Color gradient: green (high) -> yellow (medium) -> red (low)
            if hp_percentage > 0.6:
                hp_color = (50, 200, 50)  # Green
            elif hp_percentage > 0.3:
                hp_color = (200, 200, 50)  # Yellow
            else:
                hp_color = (200, 50, 50)  # Red

            pygame.draw.rect(self.screen, hp_color,
                             (bar_x, bar_y, hp_width, bar_height))

        # Draw border
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (bar_x, bar_y, bar_width, bar_height), 1)

    def _draw_unit(self, unit, army_color):
        """Helper function to draw a single unit with smooth position."""
        interp_pos = self._get_interpolated_position(unit)
        if interp_pos is None:
            return

        iso_x, iso_y = self.convert_to_iso(interp_pos)
        IMAGE = self.PIKEMAN_IMAGE
        if isinstance(unit, Knight):
            IMAGE = self.KNIGHT_IMAGE
        elif isinstance(unit, Pikeman):
            IMAGE = self.PIKEMAN_IMAGE
        elif isinstance(unit, Crossbowman):
            IMAGE = self.CROSSBOWMAN_IMAGE
        elif isinstance(unit, Monk):
            IMAGE = self.MONK_IMAGE
        elif isinstance(unit, Castle):
            IMAGE = self.CASTLE_IMAGE
        elif isinstance(unit, Elephant):
            IMAGE = self.ELEPHANT_IMAGE
        elif isinstance(unit, Rocher):
            IMAGE = self.ROCHER_IMAGE

        # Make units bigger by multiplying with unit_scale_multiplier
        unit_size = int(unit.size * self.zoom_factor * self.unit_scale_multiplier)
        unit_image = pygame.transform.scale(IMAGE, (unit_size, unit_size))
        rect = unit_image.get_rect(center=(iso_x, iso_y))
        self.screen.blit(unit_image, rect.topleft)

        if army_color is not None:
            # Draw colored border circle to identify army
            border_radius = unit_size // 2 + 3
            pygame.draw.circle(self.screen, army_color, (int(iso_x), int(iso_y)), border_radius, 2)

            # Draw HP bar above unit
            self._draw_hp_bar(unit, iso_x, iso_y, unit_size)

    def afficher(self, map: Map, army1: Army, army2: Army):
        # Handle input for camera movement and zoom
        input_result = self.handle_input()
        if input_result == "QUIT":
            return "QUIT"  # Signal to quit
        elif input_result == "LOAD":
            return "LOAD"  # Signal to load

        self.screen.fill((0, 0, 0))
        x_max, x_min, y_max, y_min = Affichage.get_sizeMap(map, army1, army2)
        # print(x_max, x_min, y_max, y_min)  # Debug output - commented out

        # Calculate actual tile size for isometric rendering
        # For isometric tiles, we need proper spacing to avoid gaps
        actual_tile_size = int(self.tile_size * self.zoom_factor)
        # Make tiles slightly larger to ensure they overlap and fill gaps
        tile_overlap = 4  # Extra pixels to ensure overlap
        tile_image = pygame.transform.scale(self.TILE_IMAGE,
                                            (actual_tile_size + tile_overlap, actual_tile_size + tile_overlap))

        for x in range(int(x_min) - 1, int(x_max) + 1):
            for y in range(int(y_min) - 1, int(y_max) + 1):
                iso_x, iso_y = self.convert_to_iso((x, y))
                
                # On choisit l'image déjà prête
                current_tile = self.TILE_LIGHT if (x + y) % 2 == 0 else self.TILE_DARK
                
                rect = current_tile.get_rect(center=(int(iso_x), int(iso_y)))
                self.screen.blit(current_tile, rect.topleft)

        # Mise à jour de l'écran

        # Draw army1 units with blue border/indicator
        for unit in army1.living_units():
            self._draw_unit(unit, (50, 100, 255))  # Blue for army1

        # Draw army2 units with red border/indicator
        for unit in army2.living_units():
            self._draw_unit(unit, (255, 50, 50))  # Red for army2

        for unit in map.obstacles:
            self._draw_unit(unit, None)

        # Draw minimap if enabled
        if self.show_minimap:
            self._draw_minimap(map, army1, army2)

        # Draw army visualization if enabled
        if self.show_army_stats:
            self._draw_army_stats(army1, army2)

        # Draw pause indicator if paused
        if self.is_paused_state:
            self._draw_pause_indicator()

        # Draw load menu if active
        if self.show_load_menu:
            self._draw_load_menu()

        pygame.display.flip()

    def is_paused(self):
        """Return pause state for Battle gameLoop."""
        return self.is_paused_state

    def _draw_pause_indicator(self):
        """Draw a pause indicator on screen."""
        # Draw semi-transparent overlay
        overlay = pygame.Surface((self.WIDTH, self.HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # Draw "PAUSED" text in center
        paused_text = self.font.render("PAUSED", True, (255, 255, 255))
        paused_rect = paused_text.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 2))

        # Draw background for text
        bg_rect = paused_rect.inflate(20, 10)
        pygame.draw.rect(self.screen, (40, 40, 40), bg_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 2)

        self.screen.blit(paused_text, paused_rect)

        # Draw instruction
        instruction = self.small_font.render("Press SPACE to resume", True, (200, 200, 200))
        inst_rect = instruction.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 2 + 40))
        self.screen.blit(instruction, inst_rect)

    def __init__(self, *args):
        super().__init__(*args)
        self.uses_pygame = True
        self.wait_for_close = True
        if len(args) > 0:
            self.path = args[0] if args[0].endswith('/') or args[0].endswith('\\') else args[0] + '/'
        else:
            self.path = "frontend/Graphics/pygame_assets/"

    def handle_input(self):
        # Process events first (for QUIT and KEYDOWN events)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"  # Signal to quit
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.show_load_menu:
                        # Close load menu instead of quitting
                        self.show_load_menu = False
                    else:
                        return "QUIT"  # Signal to quit
                elif event.key == pygame.K_m:
                    # Toggle minimap
                    self.show_minimap = not self.show_minimap
                elif event.key == pygame.K_F1:
                    # Toggle all army stats
                    self.show_army_stats = not self.show_army_stats
                elif event.key == pygame.K_F2:
                    # Toggle army1 details
                    self.show_army1_details = not self.show_army1_details
                elif event.key == pygame.K_F3:
                    # Toggle army2 details
                    self.show_army2_details = not self.show_army2_details
                elif event.key == pygame.K_F4:
                    # Toggle unit type counts
                    self.show_unit_counts = not self.show_unit_counts
                elif event.key == pygame.K_z:
                    # Increase battle speed (faster ticks)
                    self.battle_speed_multiplier = max(0.1,
                                                       self.battle_speed_multiplier * 0.7)  # Decrease delay = faster
                    print(f"Battle speed: {1.0 / self.battle_speed_multiplier:.1f}x (faster)")
                elif event.key == pygame.K_x:
                    # Decrease battle speed (slower ticks)
                    self.battle_speed_multiplier = min(5.0,
                                                       self.battle_speed_multiplier * 1.4)  # Increase delay = slower
                    print(f"Battle speed: {1.0 / self.battle_speed_multiplier:.1f}x (slower)")
                elif event.key == pygame.K_SPACE:
                    # Toggle pause
                    self.is_paused_state = not self.is_paused_state
                    if self.is_paused_state:
                        print("Battle PAUSED - Press SPACE to resume")
                    else:
                        print("Battle RESUMED")
                elif event.key == pygame.K_F11:
                    # Quick save
                    if self.battle_instance:
                        self._quick_save()
                elif event.key == pygame.K_F12:
                    # Quick load - show file selection menu
                    if self.battle_instance:
                        self.show_load_menu = True
                        self.load_menu_selected_index = 0
                elif event.key == pygame.K_ESCAPE and self.show_load_menu:
                    # Cancel load menu
                    self.show_load_menu = False
                elif event.key == pygame.K_RETURN and self.show_load_menu:
                    # Confirm load selection
                    self.show_load_menu = False
                    return "LOAD"  # Signal to load with selected file
                elif self.show_load_menu:
                    # Navigate menu with arrow keys
                    if event.key == pygame.K_UP:
                        self.load_menu_selected_index = max(0, self.load_menu_selected_index - 1)
                    elif event.key == pygame.K_DOWN:
                        save_files = self._get_save_files()
                        self.load_menu_selected_index = min(len(save_files) - 1, self.load_menu_selected_index + 1)
                    elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6,
                                       pygame.K_7, pygame.K_8, pygame.K_9]:
                        # Select by number key (1-9)
                        num = event.key - pygame.K_1
                        save_files = self._get_save_files()
                        if num < len(save_files):
                            self.load_menu_selected_index = num
                            self.show_load_menu = False
                            return "LOAD"  # Load immediately

        # Then check for held keys (for continuous movement)
        keys = pygame.key.get_pressed()
        # Déplacement avec les flèches (adjusted for isometric view)
        # Speed is relative to zoom factor for consistent feel
        base_camera_speed = 15
        camera_speed = int(base_camera_speed * (self.zoom_factor / 20))  # Scale with zoom
        if keys[pygame.K_LEFT]:
            self.offset_x += camera_speed
        if keys[pygame.K_RIGHT]:
            self.offset_x -= camera_speed
        if keys[pygame.K_UP]:
            self.offset_y += camera_speed
        if keys[pygame.K_DOWN]:
            self.offset_y -= camera_speed

        if keys[pygame.K_c]:
            self.offset_x, self.offset_y = 0, 0
            self.zoom_factor = 3

        if keys[pygame.K_1]:
            self.zoom_factor *= 1.05
        if keys[pygame.K_2]:
            self.zoom_factor /= 1.05

        return True

    def convert_to_iso(self, coor: tuple):
        x, y = coor
        # Improved isometric conversion - tiles should overlap properly
        # The spacing needs to match the tile size accounting for zoom
        scaled_tile_size = self.tile_size * self.zoom_factor
        iso_x = ((x - y) * scaled_tile_size // 2 + self.WIDTH // 2 + self.offset_x)
        iso_y = ((x + y) * scaled_tile_size // 4 + self.HEIGHT // 4 + self.offset_y)
        return (iso_x, iso_y)

    def _draw_minimap(self, map: Map, army1: Army, army2: Army):
        """Draw a minimap in the top-right corner showing the entire map."""
        minimap_x, minimap_y = self.minimap_position
        minimap_surface = pygame.Surface((self.minimap_size, self.minimap_size))
        minimap_surface.fill((40, 40, 40))  # Dark background

        # Get map bounds
        if hasattr(map, 'width') and hasattr(map, 'height'):
            map_width = map.width
            map_height = map.height
        else:
            x_max, x_min, y_max, y_min = Affichage.get_sizeMap(map, army1, army2)
            map_width = max(x_max - x_min + 1, 1)
            map_height = max(y_max - y_min + 1, 1)

        # Calculate scale
        scale_x = self.minimap_size / max(map_width, 1)
        scale_y = self.minimap_size / max(map_height, 1)

        # Draw map tiles (simplified)
        for x in range(map_width):
            for y in range(map_height):
                minimap_x_pos = int(x * scale_x)
                minimap_y_pos = int(y * scale_y)
                pygame.draw.rect(minimap_surface, (50, 150, 50),
                                 (minimap_x_pos, minimap_y_pos, int(scale_x) + 1, int(scale_y) + 1))

        # Draw units on minimap
        for unit in army1.living_units():
            if unit.position is not None:
                x, y = unit.position
                minimap_x_pos = int(x * scale_x)
                minimap_y_pos = int(y * scale_y)
                pygame.draw.circle(minimap_surface, (50, 100, 255),
                                   (minimap_x_pos, minimap_y_pos), 2)

        for unit in army2.living_units():
            if unit.position is not None:
                x, y = unit.position
                minimap_x_pos = int(x * scale_x)
                minimap_y_pos = int(y * scale_y)
                pygame.draw.circle(minimap_surface, (255, 50, 50),
                                   (minimap_x_pos, minimap_y_pos), 2)

        # Draw border
        pygame.draw.rect(minimap_surface, (255, 255, 255),
                         (0, 0, self.minimap_size, self.minimap_size), 2)

        # Blit minimap to screen
        self.screen.blit(minimap_surface, (minimap_x, minimap_y))

        # Draw minimap label
        label = self.small_font.render("Minimap (M)", True, (255, 255, 255))
        self.screen.blit(label, (minimap_x, minimap_y - 20))

    def _draw_army_stats(self, army1: Army, army2: Army):
        """Draw army statistics panel showing unit counts and types."""
        panel_x = 10
        panel_y = 10
        panel_width = 300
        line_height = 25
        current_y = panel_y

        # Background panel
        panel_surface = pygame.Surface((panel_width, 400))
        panel_surface.set_alpha(200)
        panel_surface.fill((20, 20, 20))
        self.screen.blit(panel_surface, (panel_x, panel_y))

        # Title
        title = self.font.render("Army Statistics (F1-F4)", True, (255, 255, 255))
        self.screen.blit(title, (panel_x + 5, current_y))
        current_y += line_height + 5

        # Army 1 stats
        if self.show_army1_details:
            army1_units = army1.living_units()
            army1_count = len(army1_units)

            header1 = self.font.render(f"Army 1 ({type(army1.general).__name__}): {army1_count} units", True, (50, 100, 255))
            self.screen.blit(header1, (panel_x + 5, current_y))
            current_y += line_height

            if self.show_unit_counts:
                # Count by unit type
                knights = sum(1 for u in army1_units if isinstance(u, Knight))
                pikemen = sum(1 for u in army1_units if isinstance(u, Pikeman))
                crossbowmen = sum(1 for u in army1_units if isinstance(u, Crossbowman))

                if knights > 0:
                    text = self.small_font.render(f"  Knights: {knights}", True, (200, 200, 200))
                    self.screen.blit(text, (panel_x + 5, current_y))
                    current_y += line_height - 5
                if pikemen > 0:
                    text = self.small_font.render(f"  Pikemen: {pikemen}", True, (200, 200, 200))
                    self.screen.blit(text, (panel_x + 5, current_y))
                    current_y += line_height - 5
                if crossbowmen > 0:
                    text = self.small_font.render(f"  Crossbowmen: {crossbowmen}", True, (200, 200, 200))
                    self.screen.blit(text, (panel_x + 5, current_y))
                    current_y += line_height - 5
            current_y += 5
        else:
            text = self.small_font.render("Army 1: (Press F2)", True, (150, 150, 150))
            self.screen.blit(text, (panel_x + 5, current_y))
            current_y += line_height

        # Separator
        pygame.draw.line(self.screen, (100, 100, 100),
                         (panel_x + 5, current_y), (panel_x + panel_width - 5, current_y))
        current_y += line_height

        # Army 2 stats
        if self.show_army2_details:
            army2_units = army2.living_units()
            army2_count = len(army2_units)

            header2 = self.font.render(f"Army 2 ({type(army2.general).__name__}): {army2_count} units", True, (255, 50, 50))
            self.screen.blit(header2, (panel_x + 5, current_y))
            current_y += line_height

            if self.show_unit_counts:
                # Count by unit type
                knights = sum(1 for u in army2_units if isinstance(u, Knight))
                pikemen = sum(1 for u in army2_units if isinstance(u, Pikeman))
                crossbowmen = sum(1 for u in army2_units if isinstance(u, Crossbowman))

                if knights > 0:
                    text = self.small_font.render(f"  Knights: {knights}", True, (200, 200, 200))
                    self.screen.blit(text, (panel_x + 5, current_y))
                    current_y += line_height - 5
                if pikemen > 0:
                    text = self.small_font.render(f"  Pikemen: {pikemen}", True, (200, 200, 200))
                    self.screen.blit(text, (panel_x + 5, current_y))
                    current_y += line_height - 5
                if crossbowmen > 0:
                    text = self.small_font.render(f"  Crossbowmen: {crossbowmen}", True, (200, 200, 200))
                    self.screen.blit(text, (panel_x + 5, current_y))
                    current_y += line_height - 5
        else:
            text = self.small_font.render("Army 2: (Press F3)", True, (150, 150, 150))
            self.screen.blit(text, (panel_x + 5, current_y))
            current_y += line_height

        # Help text
        current_y += 10
        help_text = [
            "Controls:",
            "M - Toggle Minimap",
            "F1 - Toggle All Stats",
            "F2 - Toggle Army 1",
            "F3 - Toggle Army 2",
            "F4 - Toggle Unit Counts",
            "F11 - Quick Save",
            "F12 - Quick Load",
            "SPACE - Pause/Resume",
            "Z/X - Speed Up/Down"
        ]
        for line in help_text:
            text = self.small_font.render(line, True, (150, 150, 150))
            self.screen.blit(text, (panel_x + 5, current_y))
            current_y += line_height - 5

    def _quick_save(self):
        """Quick save the current battle state."""
        import os
        from pathlib import Path

        if not self.battle_instance:
            print("Error: No battle instance to save")
            return

        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saves")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, self.quick_save_filename)

        try:
            data = self.battle_instance.to_dict()
            # Atomic write: write to temp then move
            tmp = Path(filepath).with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, filepath)
            print(f"Quick save successful: {filepath}")
        except Exception as e:
            print(f"Error saving battle: {e}")

    def set_battle_instance(self, battle):
        """Set the battle instance for save/load operations."""
        self.battle_instance = battle

    def _get_save_files(self):
        """Get list of available save files."""
        import os
        import glob

        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saves")
        if not os.path.exists(save_dir):
            return []

        # Get all .json files in saves directory
        pattern = os.path.join(save_dir, "*.json")
        files = glob.glob(pattern)
        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)
        # Return just the filenames
        return [os.path.basename(f) for f in files]

    def _draw_load_menu(self):
        """Draw the file selection menu for loading saves."""
        save_files = self._get_save_files()

        if not save_files:
            # No save files available
            overlay = pygame.Surface((self.WIDTH, self.HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

            no_saves_text = self.font.render("No save files found", True, (255, 255, 255))
            no_saves_rect = no_saves_text.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 2))
            self.screen.blit(no_saves_text, no_saves_rect)

            esc_text = self.small_font.render("Press ESC to close", True, (200, 200, 200))
            esc_rect = esc_text.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 2 + 40))
            self.screen.blit(esc_text, esc_rect)
            return

        # Menu dimensions
        menu_width = 500
        menu_height = min(600, 50 + len(save_files) * 40)
        menu_x = (self.WIDTH - menu_width) // 2
        menu_y = (self.HEIGHT - menu_height) // 2

        # Draw background
        menu_surface = pygame.Surface((menu_width, menu_height))
        menu_surface.fill((40, 40, 40))
        pygame.draw.rect(menu_surface, (255, 255, 255), (0, 0, menu_width, menu_height), 2)
        self.screen.blit(menu_surface, (menu_x, menu_y))

        # Title
        title = self.font.render("Select Save File to Load", True, (255, 255, 255))
        title_rect = title.get_rect(center=(menu_x + menu_width // 2, menu_y + 25))
        self.screen.blit(title, title_rect)

        # Draw file list
        start_y = menu_y + 60
        max_visible = min(len(save_files), 12)  # Show max 12 files
        start_index = max(0, min(self.load_menu_selected_index - 5, len(save_files) - max_visible))

        for i in range(start_index, min(start_index + max_visible, len(save_files))):
            filename = save_files[i]
            y_pos = start_y + (i - start_index) * 40

            # Highlight selected item
            if i == self.load_menu_selected_index:
                pygame.draw.rect(self.screen, (100, 100, 200),
                                 (menu_x + 10, y_pos - 5, menu_width - 20, 35))

            # File name
            display_name = filename
            if len(display_name) > 40:
                display_name = display_name[:37] + "..."

            # Number label
            num_text = self.small_font.render(f"{i + 1}.", True, (200, 200, 200))
            self.screen.blit(num_text, (menu_x + 20, y_pos))

            # File name
            name_text = self.small_font.render(display_name, True, (255, 255, 255))
            self.screen.blit(name_text, (menu_x + 60, y_pos))

        # Instructions
        inst_y = menu_y + menu_height - 40
        instructions = [
            "UP/DOWN: Navigate  |  ENTER: Load  |  ESC: Cancel",
            "Or press 1-9 to load directly"
        ]
        for j, inst in enumerate(instructions):
            inst_text = self.small_font.render(inst, True, (150, 150, 150))
            inst_rect = inst_text.get_rect(center=(menu_x + menu_width // 2, inst_y + j * 20))
            self.screen.blit(inst_text, inst_rect)

    def _quick_load(self, filename=None):
        """Quick load a saved battle state."""
        import os

        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saves")

        # Use selected filename or default
        if filename is None:
            save_files = self._get_save_files()
            if not save_files:
                print("Error: No save files found")
                return None
            # Use selected file from menu
            if 0 <= self.load_menu_selected_index < len(save_files):
                filename = save_files[self.load_menu_selected_index]
            else:
                filename = self.quick_save_filename

        filepath = os.path.join(save_dir, filename)

        if not os.path.exists(filepath):
            print(f"Error: Save file not found: {filepath}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                import json
                data = json.load(f)

            from backend.GameModes.Battle import Battle
            loaded_battle = Battle.from_dict(data)
            print(f"Quick load successful: {filepath}")
            return loaded_battle
        except Exception as e:
            print(f"Error loading battle: {e}")
            import traceback
            traceback.print_exc()
            return None