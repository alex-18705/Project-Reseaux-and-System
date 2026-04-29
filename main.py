import argparse
import os

from backend.GameModes.Battle import Battle
from backend.GameModes.Online import Online
from backend.GameModes.TestOnline import TestOnline
from backend.Utils.class_by_name import general_from_name, get_available_generals
from backend.Utils.file_loader import load_mirrored_army_from_file, load_map_from_file, load_army_from_file
from frontend.Terminal import Screen
from frontend.Terminal.NoAffiche import NoAffiche


import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error:
            return True

def find_available_ports(start_py=5000, start_lan=6000):
    py_port = start_py
    lan_port = start_lan
    while is_port_in_use(py_port) or is_port_in_use(lan_port):
        py_port += 1
        lan_port += 1
    return py_port, lan_port

def main():
    parser = argparse.ArgumentParser(description="MedievAIl Battle Simulator")
    subparsers = parser.add_subparsers(dest="mode")

    # ==================== RUN ====================
    run_parser = subparsers.add_parser("run", help="Run a new battle")

    run_parser.add_argument(
        "--ticks", "-t", type=int, default=None,
        help="Maximum ticks to run the battle (omit to run until end)"
    )

    run_parser.add_argument(
        "--general1", "-g1", type=str, default=None,
        help=f"Comma-separated list of generals.  Available: {', '.join(get_available_generals())}"
    )
    run_parser.add_argument(
        "--general2", "-g2", type=str, default=None,
        help=f"Comma-separated list of generals.  Available: {', '.join(get_available_generals())}"
    )
    run_parser.add_argument(
        "--army_file", type=str,
        help="path of the army repartition file"
    )
    run_parser.add_argument(
        "--map_file", type=str,
        help="path of the map file"
    )
    run_parser.add_argument(
        "--curses", action="store_true", dest="use_curses",
        help="Use curses-based terminal display if available"
    )
    run_parser.add_argument(
        "--pygame", action="store_true", dest="use_pygame",
        help="Use pygame graphical display if available"
    )

    # ==================== ONLINE ====================
    run_parser = subparsers.add_parser("online", help="Run a new online battle")

    run_parser.add_argument(
        "--general", "-g", type=str, default=None,
        help=f"Comma-separated list of generals.  Available: {', '.join(get_available_generals())}"
    )
    run_parser.add_argument(
        "--army_file", type=str,
        help="path of the army repartition file"
    )
    run_parser.add_argument(
        "--map_file", type=str,
        help="path of the map file"
    )
    run_parser.add_argument(
        "--curses", action="store_true", dest="use_curses",
        help="Use curses-based terminal display if available"
    )
    run_parser.add_argument(
        "--pygame", action="store_true", dest="use_pygame",
        help="Use pygame graphical display if available"
    )
    run_parser.add_argument(
        "--create", action="store_true", dest="create",
        help="Start online mode with no know ip"
    )
    run_parser.add_argument(
        "--join", type=str,
        help="--join <ip>"
    )
    run_parser.add_argument(
        "--py_port", type=int, default=None,
        help="Local port for Python-Proxy communication (auto-detected if omitted)"
    )
    run_parser.add_argument(
        "--lan_port", type=int, default=None,
        help="Local port for LAN communication (auto-detected if omitted)"
    )
    run_parser.add_argument(
        "--remote_port", type=int, default=6000,
        help="Target port on the remote machine (default: 6000)"
    )
    run_parser.add_argument(
        "--ticks", "-t", type=int, default=None,
        help="Maximum ticks to run the online battle (omit to run until end)"
    )
    run_parser.add_argument(
        "--spawn_slot", type=int, default=None,
        help="Deployment slot for online mode: 0=host side, 1/2/...=separate joiner lanes"
    )

    # ==================== TestOnline ====================
    run_parser = subparsers.add_parser("testOnline", help="Test online")
    run_parser.add_argument(
        "--ticks", "-t", type=int, default=None,
        help="Maximum ticks to run the battle (omit to run until end)"
    )



    args = parser.parse_args()

    gameMode = None

    # ==================== MODE:  ONLINE ====================
    if args.mode == "online":
        # Automatic port allocation if not provided
        py_port = args.py_port
        lan_port = args.lan_port
        if py_port is None or lan_port is None:
            py_port, lan_port = find_available_ports(py_port or 5000, lan_port or 6000)
            print(f"[Online] Auto-allocation : py_port={py_port}, lan_port={lan_port}")

        # If args.join is None, we are the host (Blue)
        is_first = args.join is None
        gameMode = Online(
            py_port=py_port,
            lan_port=lan_port,
            remote_port=args.remote_port,
            is_first=is_first,
            spawn_slot=args.spawn_slot
        )
        gameMode.max_tick = args.ticks

        if args.join : gameMode.know_ip.add(args.join)

        print(gameMode.know_ip)

        map_obj = load_map_from_file(args.map_file)
        gameMode.my_army = load_army_from_file(args.army_file)

        general = general_from_name(args.general)()

        gameMode.my_army.general = general
        general.army = gameMode.my_army

        gameMode.map = map_obj

        affichage = NoAffiche()
        if args.use_pygame:
            from frontend.Graphics.PyScreen import PyScreen
            affichage = PyScreen(os.getcwd() + "/frontend/Graphics/pygame_assets/")
        elif args.use_curses:
            affichage = Screen()

        gameMode.affichage = affichage

        # Skip blocking save prompt for online mode to allow immediate connection
        # choice = input("Do you want to save this battle? (y/N): ")
        # if choice.lower().startswith("y"):
        #    gameMode.isSave = True

        gameMode.launch()
        gameMode.gameLoop()
        gameMode.end()

    # ==================== MODE:  RUN ====================
    if args.mode == "run":
            battle = Battle()
            battle.max_tick = args.ticks
            gameMode = battle

            army1, army2 = load_mirrored_army_from_file(args.army_file)
            map_obj = load_map_from_file(args.map_file)

            gameMode.army1 = army1
            gameMode.army2 = army2

            general1 = general_from_name(args.general1)()
            general2 = general_from_name(args.general2)()

            army1.general = general1
            general1.army = army1
            army2.general = general2
            general2.army = army2

            gameMode.map = map_obj

            affichage = NoAffiche()
            if args.use_pygame:
                from frontend.Graphics.PyScreen import PyScreen
                affichage = PyScreen(os.getcwd() + "/frontend/Graphics/pygame_assets/")
            elif args.use_curses:
                affichage = Screen()

            gameMode.affichage = affichage

            choice = input("Do you want to save this battle? (y/N): ")
            if choice.lower().startswith("y"):
                gameMode.isSave = True

            gameMode.launch()
            gameMode.gameLoop()
            gameMode.end()

    # ==================== MODE:  TestOnline ====================
    if args.mode == "testOnline":
            testOnline = TestOnline()
            testOnline.max_tick = args.ticks
            gameMode = testOnline

            affichage = NoAffiche()

            testOnline.affichage = affichage

            testOnline.launch()
            testOnline.gameLoop()
            testOnline.end()




if __name__ == "__main__":
    main()
