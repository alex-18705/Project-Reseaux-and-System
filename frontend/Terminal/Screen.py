# frontend/Terminal/Screen.py
import curses
import html
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from backend.Class.Obstacles.Obstacle import Obstacle
from backend.Class.Obstacles.Rocher import Rocher
from backend.Class.Units.Castle import Castle
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Units.Elephant import Elephant
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Monk import Monk
from backend.Class.Units.Pikeman import Pikeman
from backend.Class.Units.Unit import Unit
from frontend.Affichage import Affichage


class Screen(Affichage):
    """
    Curses-based terminal renderer that satisfies the "terminal map view" requirement.
    - Uses ASCII symbols to show units/obstacles.
    - Allows scrolling with arrows or ZQSD (upper-case for faster moves).
    - Press P to pause/resume battle ticks.
    - Press TAB to pause and dump an HTML snapshot of every unit/general, then opens it in the browser.
    - Press ESC or Q to exit the terminal view.
    """

    OBSTACLE_CHAR = "#"

    def __init__(self):
        super().__init__()
        self.std: Optional[curses.window] = None
        self.x = 0
        self.y = 0
        self.grille: List[List[str]] = []
        self.log_lines: List[str] = []
        self.status_msg = ""
        self.paused = False
        self.uses_pygame = False  # helps Battle know we don't need pygame clock
        self.wait_for_close = True
        self.snapshot_dir = Path("snapshots")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._grid_width = 0
        self._grid_height = 0
        # Save/Load control
        self.quick_save_filename = "quicksave.json"
        self.battle_instance = None  # Will be set by Battle gameLoop
        self.show_load_menu = False  # Show file selection menu
        self.load_menu_selected_index = 0  # Currently selected file index

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def initialiser(self):
        if self.std is not None:
            return
        self.std = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.std.nodelay(True)
        self.std.keypad(True)
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.status_msg = "Terminal ready (Arrows/ZQSD scroll, P pause, TAB snapshot, S save, L load, ESC quit)"

    # Legacy helper so old callers that expect `start()` still work.
    def start(self):
        self.initialiser()

    def shutdown(self):
        if self.std is None:
            return
        try:
            curses.nocbreak()
            self.std.keypad(False)
            curses.echo()
            curses.endwin()
        finally:
            self.std = None

    def getch(self):
        if self.std is None:
            return None
        key = self.std.getch()
        return None if key == curses.ERR else key

    # ------------------------------------------------------------------ #
    # Battle hooks
    # ------------------------------------------------------------------ #
    def is_paused(self) -> bool:
        return self.paused

    def afficher(self, map, army1, army2):
        if self.std is None:
            self.initialiser()

        grid = self._build_grid(map, army1, army2)
        self.actualiser_grille(grid)
        self.actualiser_log(self._build_log_lines(army1, army2))

        action = self.handle_input(map, army1, army2)
        if action == "quit":
            return "QUIT"

        self.afficher_grille()
        return None

    # ------------------------------------------------------------------ #
    # Grid construction helpers
    # ------------------------------------------------------------------ #
    def _build_grid(self, game_map, army1, army2):
        width = self._resolve_width(game_map, army1, army2)
        height = self._resolve_height(game_map, army1, army2)
        self._grid_width = width
        self._grid_height = height

        grid = [[ "." for _ in range(width)] for _ in range(height)]

        # Obstacles (approximate circle footprint)
        #for obstacle in getattr(game_map, "obstacles", []):
        #    self._mark_obstacle(grid, obstacle)

        # Units
        for unit in army1.living_units():
            self._place_unit(grid, unit, player_one=True)
        for unit in army2.living_units():
            self._place_unit(grid, unit, player_one=False)
        for obstacle in game_map.obstacles :
            self._place_unit(grid, obstacle)

        return grid

    def _resolve_width(self, game_map, army1, army2):
        width = getattr(game_map, "width", 0)
        if width:
            return int(width)
        use_army1 = army1 or (self.gameMode.army1 if self.gameMode else None)
        use_army2 = army2 or (self.gameMode.army2 if self.gameMode else None)
        x_max, x_min, _, _ = Affichage.get_sizeMap(game_map, use_army1, use_army2)
        return max(1, int(x_max - x_min + 1))

    def _resolve_height(self, game_map, army1, army2):
        height = getattr(game_map, "height", 0)
        if height:
            return int(height)
        use_army1 = army1 or (self.gameMode.army1 if self.gameMode else None)
        use_army2 = army2 or (self.gameMode.army2 if self.gameMode else None)
        _, _, y_max, y_min = Affichage.get_sizeMap(game_map, use_army1, use_army2)
        return max(1, int(y_max - y_min + 1))

    def _clamp_indices(self, x, y):
        ix = max(0, min(self._grid_width - 1, x))
        iy = max(0, min(self._grid_height - 1, y))
        return ix, iy

    def _mark_obstacle(self, grid, obstacle):
        pos = getattr(obstacle, "position", None)
        size = getattr(obstacle, "size", 1)
        if not pos:
            return
        radius = max(1, int(round(size)))
        ox = int(round(pos[0]))
        oy = int(round(pos[1]))
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx * dx + dy * dy > radius * radius:
                    continue
                ix, iy = self._clamp_indices(ox + dx, oy + dy)
                grid[iy][ix] = self.OBSTACLE_CHAR

    def _place_unit(self, grid, unit, player_one: bool= False):
        if unit.position is None:
            return
        ux = int(round(unit.position[0]))
        uy = int(round(unit.position[1]))
        ix, iy = self._clamp_indices(ux, uy)
        if isinstance(unit,Unit) :
            grid[iy][ix] = self._symbol_for_unit(unit, player_one)
        elif isinstance(unit, Obstacle) :
            grid[iy][ix] = self._symbol_for_obstacle(unit)

    def _symbol_for_obstacle(self, unit):
        mapping = {
            Rocher : "O"
        }
        base = mapping.get(type(unit), "O")
        return base


    def _symbol_for_unit(self, unit, player_one: bool):
        mapping = {
            Knight: "K",
            Pikeman: "P",
            Crossbowman: "C",
            Castle : "H",
            Elephant : "E",
            Monk : "M",
        }
        base = mapping.get(type(unit), "U")
        return base if player_one else base.lower()

    # ------------------------------------------------------------------ #
    # Rendering helpers
    # ------------------------------------------------------------------ #
    def actualiser_grille(self, grille: List[List[object]]):
        self.grille = grille
        if not self.grille:
            self.x = 0
            self.y = 0
            return
        height = len(self.grille)
        width = len(self.grille[0])
        self._grid_height = height
        self._grid_width = width
        self.x = max(0, min(self.x, max(0, width - 1)))
        self.y = max(0, min(self.y, max(0, height - 1)))

    def actualiser_log(self, lines: Optional[List[str]]):
        if not lines:
            self.log_lines = []
            return
        self.log_lines = list(lines)[-5:]

    def afficher_grille(self):
        if self.std is None:
            return
        self.std.erase()
        maxy, maxx = self.std.getmaxyx()

        help_height = 1
        status_height = 1
        log_height = min(5, max(0, maxy // 6))
        grid_area_height = maxy - help_height - status_height - log_height - 2
        usable_h = max(1, grid_area_height)
        usable_w = max(2, maxx - 2)

        if not self.grille:
            try:
                self.std.addstr(0, 0, "No data")
            except curses.error:
                pass
            self.std.refresh()
            return

        grid_h = len(self.grille)
        grid_w = len(self.grille[0])
        self.y = max(0, min(self.y, max(0, grid_h - usable_h)))
        self.x = max(0, min(self.x, max(0, grid_w - usable_w)))
        min_y = self.y
        max_y = min(grid_h, self.y + usable_h)
        min_x = self.x
        max_x = min(grid_w, self.x + usable_w)

        top_row = "-" * (max_x - min_x)
        try:
            self.std.addstr(0, 1, top_row[:usable_w])
        except curses.error:
            pass

        for row_idx, y in enumerate(range(min_y, max_y), start=1):
            line_chars = []
            for x in range(min_x, max_x):
                cell = self.grille[y][x]
                ch = str(cell) if cell is not None else "."
                if not ch:
                    ch = "."
                line_chars.append(ch[0])
            line = "".join(line_chars)
            try:
                self.std.addstr(row_idx, 1, line[:usable_w])
            except curses.error:
                pass

        bottom_row = "-" * (max_x - min_x)
        try:
            self.std.addstr(1 + (max_y - min_y), 1, bottom_row[:usable_w])
        except curses.error:
            pass

        log_start_row = 2 + (max_y - min_y)
        for i, logline in enumerate(self.log_lines[-log_height:]):
            row = log_start_row + i
            text = str(logline)[:usable_w]
            try:
                self.std.addstr(row, 1, text.ljust(usable_w)[:usable_w])
            except curses.error:
                pass

        status_row = maxy - 2
        help_row = maxy - 1
        status_text = (self.status_msg or "").ljust(maxx - 1)
        help_text = "ESC quit | Arrows/ZQSD (Shift fast) | P pause | TAB snapshot | S save | L load"
        try:
            self.std.addstr(status_row, 0, status_text[:maxx - 1])
            self.std.addstr(help_row, 0, help_text[:maxx - 1])
        except curses.error:
            pass

        self.std.refresh()

    # ------------------------------------------------------------------ #
    # Input & snapshot
    # ------------------------------------------------------------------ #
    def handle_input(self, game_map, army1, army2):
        if self.std is None:
            return None
        action = None
        while True:
            key = self.std.getch()
            if key == curses.ERR:
                break

            if key in (ord('p'), ord('P')):
                self.paused = not self.paused
                state = "Paused" if self.paused else "Running"
                self.set_status(state)
            elif key == 9:  # TAB
                self.paused = True
                path = self._write_snapshot(game_map, army1, army2)
                self.set_status(f"Snapshot saved to {path}")
                try:
                    webbrowser.open(path.resolve().as_uri(), new=2)
                except Exception:
                    pass
            elif key in (ord('s'), ord('S')):
                # Quick save
                if self.battle_instance:
                    self._quick_save()
                else:
                    self.set_status("No battle instance to save")
            elif key in (ord('l'), ord('L')):
                # Quick load - show file selection menu
                if self.battle_instance:
                    self.show_load_menu = True
                    self.load_menu_selected_index = 0
                    action = self._show_load_menu()
                    if action == "load":
                        return "LOAD"  # Signal to load
                    elif action == "quit":
                        return "quit"
            elif key == 27:  # ESC quits the terminal view
                if self.show_load_menu:
                    self.show_load_menu = False
                else:
                    action = "quit"
                    break
            else:
                if not self.show_load_menu:
                    self._handle_scroll(key)
                else:
                    # Handle menu navigation
                    if key == curses.KEY_UP:
                        self.load_menu_selected_index = max(0, self.load_menu_selected_index - 1)
                    elif key == curses.KEY_DOWN:
                        save_files = self._get_save_files()
                        self.load_menu_selected_index = min(len(save_files) - 1, self.load_menu_selected_index + 1)
                    elif key == 10 or key == 13:  # Enter
                        self.show_load_menu = False
                        return "LOAD"
                    elif ord('1') <= key <= ord('9'):
                        # Direct selection by number
                        num = key - ord('1')
                        save_files = self._get_save_files()
                        if num < len(save_files):
                            self.load_menu_selected_index = num
                            self.show_load_menu = False
                            return "LOAD"
        return action

    def _handle_scroll(self, key):
        step = 1
        if 0 <= key <= 255:
            ch = chr(key)
            if ch.isalpha() and ch.isupper():
                step = 5

        if key in (curses.KEY_UP, ord('k'), ord('K'), ord('z'), ord('Z')):
            self.y = max(0, self.y - step)
        elif key in (curses.KEY_DOWN, ord('j'), ord('J'), ord('s'), ord('S')):
            self.y = min(max(0, self._grid_height - 1), self.y + step)
        elif key in (curses.KEY_LEFT, ord('h'), ord('H'), ord('q'), ord('Q')):
            self.x = max(0, self.x - step)
        elif key in (curses.KEY_RIGHT, ord('l'), ord('L'), ord('d'), ord('D')):
            self.x = min(max(0, self._grid_width - 1), self.x + step)

    def _write_snapshot(self, game_map, army1, army2):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.snapshot_dir / f"battle_snapshot_{timestamp}.html"

        general1 = getattr(army1, "general", None)
        general2 = getattr(army2, "general", None)
        tick = getattr(self.gameMode, "tick", 0)

        def unit_rows(owner_name, army):
            rows = []
            for unit in army.units:
                status = "Alive" if unit.is_alive() else "Dead"
                pos = unit.position if unit.position is not None else ("?", "?")
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(owner_name)}</td>"
                    f"<td>{html.escape(unit.unit_type())}</td>"
                    f"<td>{pos[0]}</td><td>{pos[1]}</td>"
                    f"<td>{unit.hp}</td>"
                    f"<td>{unit.attack}</td>"
                    f"<td>{unit.armor}</td>"
                    f"<td>{unit.range}</td>"
                    f"<td>{unit.cooldown}</td>"
                    f"<td>{status}</td>"
                    "</tr>"
                )
            return "\n".join(rows)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Battle snapshot - tick {tick}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #111; color: #eee; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #444; padding: 4px 6px; text-align: center; }}
    th {{ background: #222; }}
    caption {{ margin-bottom: 0.5rem; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>Battle snapshot</h1>
  <p>Tick: {tick}</p>
  <p>Army 1 General: {html.escape(general1.__class__.__name__ if general1 else "No general")}</p>
  <p>Army 2 General: {html.escape(general2.__class__.__name__ if general2 else "No general")}</p>
  <table>
    <caption>Units</caption>
    <thead>
      <tr>
        <th>Army</th><th>Type</th><th>X</th><th>Y</th>
        <th>HP</th><th>Attack</th><th>Armor</th><th>Range</th>
        <th>Cooldown</th><th>Status</th>
      </tr>
    </thead>
    <tbody>
      {unit_rows("Army 1", army1)}
      {unit_rows("Army 2", army2)}
    </tbody>
  </table>
</body>
</html>
"""
        path.write_text(html_content, encoding="utf-8")
        return path

    # ------------------------------------------------------------------ #
    # Status helpers
    # ------------------------------------------------------------------ #
    def set_status(self, message: str):
        self.status_msg = message or ""

    def clear_status(self):
        self.status_msg = ""

    def _build_log_lines(self, army1, army2):
        tick = getattr(self.gameMode, "tick", 0)
        lines = [
            f"Tick {tick} | {'PAUSED' if self.paused else 'RUNNING'}",
            f"Army1: {len(army1.living_units())}/{len(army1.units)} alive",
            f"Army2: {len(army2.living_units())}/{len(army2.units)} alive",
        ]
        general1 = getattr(army1, "general", None)
        general2 = getattr(army2, "general", None)
        if general1:
            lines.append(f"G1: {general1.__class__.__name__}")
        if general2:
            lines.append(f"G2: {general2.__class__.__name__}")
        return lines
    
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
    
    def _quick_save(self):
        """Quick save the current battle state."""
        import os
        from pathlib import Path
        
        if not self.battle_instance:
            self.set_status("Error: No battle instance to save")
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
            self.set_status(f"Quick save successful: {filepath}")
        except Exception as e:
            self.set_status(f"Error saving battle: {e}")
    
    def _quick_load(self, filename=None):
        """Quick load a saved battle state."""
        import os
        
        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saves")
        
        # Use selected filename or default
        if filename is None:
            save_files = self._get_save_files()
            if not save_files:
                self.set_status("Error: No save files found")
                return None
            # Use selected file from menu
            if 0 <= self.load_menu_selected_index < len(save_files):
                filename = save_files[self.load_menu_selected_index]
            else:
                filename = self.quick_save_filename
        
        filepath = os.path.join(save_dir, filename)
        
        if not os.path.exists(filepath):
            self.set_status(f"Error: Save file not found: {filepath}")
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                import json
                data = json.load(f)
            
            from backend.GameModes.Battle import Battle
            loaded_battle = Battle.from_dict(data)
            self.set_status(f"Quick load successful: {filepath}")
            return loaded_battle
        except Exception as e:
            self.set_status(f"Error loading battle: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _show_load_menu(self):
        """Show file selection menu for loading saves (curses-based)."""
        if self.std is None:
            return None
        
        save_files = self._get_save_files()
        if not save_files:
            self.set_status("No save files found. Press ESC to close.")
            return None
        
        self.show_load_menu = True
        self.load_menu_selected_index = 0
        
        # Draw menu
        maxy, maxx = self.std.getmaxyx()
        menu_height = min(len(save_files) + 4, maxy - 4)
        menu_width = min(60, maxx - 4)
        start_y = (maxy - menu_height) // 2
        start_x = (maxx - menu_width) // 2
        
        # Clear and redraw
        self.std.erase()
        
        # Draw border
        try:
            self.std.addstr(start_y, start_x, "┌" + "─" * (menu_width - 2) + "┐")
            self.std.addstr(start_y + menu_height - 1, start_x, "└" + "─" * (menu_width - 2) + "┘")
            for i in range(1, menu_height - 1):
                self.std.addstr(start_y + i, start_x, "│")
                self.std.addstr(start_y + i, start_x + menu_width - 1, "│")
        except curses.error:
            pass
        
        # Title
        title = "Select Save File to Load"
        try:
            self.std.addstr(start_y + 1, start_x + (menu_width - len(title)) // 2, title)
        except curses.error:
            pass
        
        # File list
        max_visible = min(len(save_files), menu_height - 4)
        start_index = max(0, min(self.load_menu_selected_index - 5, len(save_files) - max_visible))
        
        for i in range(start_index, min(start_index + max_visible, len(save_files))):
            y_pos = start_y + 3 + (i - start_index)
            filename = save_files[i]
            display_name = filename
            if len(display_name) > menu_width - 8:
                display_name = display_name[:menu_width - 11] + "..."
            
            # Highlight selected
            attr = curses.A_REVERSE if i == self.load_menu_selected_index else 0
            try:
                line = f"{i+1}. {display_name}"
                self.std.addstr(y_pos, start_x + 2, line[:menu_width - 4], attr)
            except curses.error:
                pass
        
        # Instructions
        inst_y = start_y + menu_height - 2
        instructions = [
            "UP/DOWN: Navigate | ENTER: Load | ESC: Cancel",
            "Or press 1-9 to load directly"
        ]
        for j, inst in enumerate(instructions):
            try:
                self.std.addstr(inst_y + j, start_x + 2, inst[:menu_width - 4])
            except curses.error:
                pass
        
        self.std.refresh()
        return None
