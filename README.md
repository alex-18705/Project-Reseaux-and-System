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

---

### Mode multi-pairs (P2P) & Ownership Manager

Ce projet supporte désormais le jeu en multi-pairs (plus de 2 joueurs) et utilise un **Ownership Manager** pour garantir la cohérence.

#### Comment tester localement (Simplifié)

Grâce à l'allocation automatique des ports, vous n'avez plus besoin de spécifier les ports manuellement pour tester sur une même machine.

**Terminal 1 (Host - Créateur)**
```powershell
python main.py online --create --general MajorDaft --army_file army/two.army --map_file map/superflat.map --pygame
```

**Terminal 2 (Client 1)**
```powershell
python main.py online --join 127.0.0.1 --general MajorDaft --army_file army/two.army --map_file map/superflat.map --pygame
```

**Terminal 3 (Client 2)**
```powershell
python main.py online --join 127.0.0.1 --general MajorDaft --army_file army/two.army --map_file map/superflat.map --pygame
```

#### Ownership Manager
L'Ownership Manager (`backend/Utils/network_ownership.py`) assure que :
- Chaque unité a un unique propriétaire identifié par son UUID.
- Seul le propriétaire peut exécuter les actions (mouvements, attaques) de ses unités.
- Les autres clients reçoivent l'état mis à jour et l'appliquent localement.
- Supporte la découverte dynamique de nouveaux pairs.
