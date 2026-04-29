# Python Project 2025–2026: MedievAIl BAIttle GenerAIl

Source :
https://drive.google.com/file/d/1BHxEBfnQlzLeh-AHwUvqT_n3qOcvhRAp/view?usp=drive_link
https://drive.google.com/file/d/1T1PBgwUbtoPRrT4uYkOi8iOA9RJ1wf_O/view?usp=drive_link

<details>
<summary>📑 Contents</summary>

- [About The Project](#about-the-project)
- [Built With](#built-with)
- [Installation](#installation)

</details>

## Built With

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-00A300?style=for-the-badge)

## Usage

### Online Battle Commands

- `python main.py online --create --pygame --army_file army\*.army --map_file map\*.map --general MajorDaft`
  Crée une bataille et attend que quelqu'un se connecte
- `python main.py online --join 192.168.10.3 --curses --army_file army\*.army --map_file map\*.map --general MajorDaft`  
  Rejoin une bataille auquel participe l'ordinateur avec l'ip 192.168.10.3.

### Offline Battle Commands

- `python main.py run --pygame --army_file army\*.army --map_file map\*.map --general1 (choose general ex: MajorDaft) --general2 (choose general ex: MajorDaft)`  
  Launches a **pygame battle** (60 FPS display).

- `python main.py run --curses --army_file army\*.army --map_file map\*.map --general1 (choose general ex: MajorDaft) --general2 (choose general ex: MajorDaft)`  
  Same setup but with the **ASCII / curses terminal view**.  
  Requires a curses-capable terminal  
  (`pip install windows-curses` on Windows).

---

### In-game Controls

#### Pygame (`PyScreen.py`)

- **Arrow keys**: pan camera (speed scales with zoom)
- **1 / 2**: zoom in / zoom out
- **C**: reset camera to center
- **Space**: pause / resume simulation (big overlay in middle)
- **Esc**: close the window (or exit load menu)
- **M**: toggle minimap
- **F1**: toggle stats panel
- **F2 / F3**: show / hide Army 1 / Army 2 details
- **F4**: toggle per-unit-type counts
- **Tab**: open quick-load menu (if implemented)
- **Mouse wheel / HZ**: not configured
- Army units show colored outlines; smooth motion handled automatically

---

#### Curses terminal view (`Screen.py`)

- **Arrow keys** or **H / J / K / L**: scroll viewport  
  (use uppercase **HJKL** or **Shift + arrows** to move faster)
- **Z / S / Q / D**: alternative ZQSD movement (uppercase for faster)
- **P**: pause / resume battle ticks
- **Tab**: pause and generate an **HTML snapshot**  
  (`battle_snapshot_*.html`) which opens in your browser
- **Esc**: exit the battle view
- **Save / Load menu** (if visible):
  - **S**: quick-save
  - **L**: open load menu

python main.py online --create --peer_id player_A --remote_peer_id player_B --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5000 --lan_port 6000 --remote_port 6001

python main.py online --join 127.0.0.1 --peer_id player_B --remote_peer_id player_A --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5001 --lan_port 6001 --remote_port 6000

python main.py online --create --peer_id player_A --spawn_index 0 --spawn_count 3 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5000 --lan_port 6000 --peer player_B:127.0.0.1:6001 --peer player_C:127.0.0.1:6002

python main.py online --create --peer_id player_B --spawn_index 1 --spawn_count 3 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5001 --lan_port 6001 --peer player_A:127.0.0.1:6000 --peer player_C:127.0.0.1:6002

python main.py online --create --peer_id player_C --spawn_index 2 --spawn_count 3 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5002 --lan_port 6002 --peer player_A:127.0.0.1:6000 --peer player_B:127.0.0.1:6001

python main.py online --create --peer_id player_D --spawn_index 3 --spawn_count 4 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5002 --lan_port 6002 --peer player_A:127.0.0.1:6000 --peer player_B:127.0.0.1:6001

# 4 PEERS

Terminal 1:
python main.py online --create --peer_id player_A --spawn_index 0 --spawn_count 4 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5000 --lan_port 6000 --peer player_B:127.0.0.1:6001 --peer player_C:127.0.0.1:6002 --peer player_D:127.0.0.1:6003

Terminal 2:
python main.py online --create --peer_id player_B --spawn_index 1 --spawn_count 4 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5001 --lan_port 6001 --peer player_A:127.0.0.1:6000 --peer player_C:127.0.0.1:6002 --peer player_D:127.0.0.1:6003

Terminal 3:
python main.py online --create --peer_id player_C --spawn_index 2 --spawn_count 4 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5002 --lan_port 6002 --peer player_A:127.0.0.1:6000 --peer player_B:127.0.0.1:6001 --peer player_D:127.0.0.1:6003

Terminal 4:
python main.py online --create --peer_id player_D --spawn_index 3 --spawn_count 4 --general MajorDaft --army_file army/cube.army --map_file map/superflat.map --pygame --py_port 5003 --lan_port 6003 --peer player_A:127.0.0.1:6000 --peer player_B:127.0.0.1:6001 --peer player_C:127.0.0.1:6002
