import argparse
import os
import subprocess
import time

from backend.GameModes.Battle import Battle
from backend.GameModes.Online import Online
from backend.GameModes.TestOnline import TestOnline
from backend.Utils.class_by_name import general_from_name, get_available_generals
from backend.Utils.file_loader import load_mirrored_army_from_file, load_map_from_file, load_army_from_file
from frontend.Terminal import Screen
from frontend.Terminal.NoAffiche import NoAffiche


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
        "--peer_id", type=str, default=None,
        help="Local peer id. Must match the id used when starting the C proxy."
    )
    run_parser.add_argument(
        "--py_port", type=int, default=5000,
        help="Local TCP port where the C proxy accepts the Python connection."
    )
    run_parser.add_argument(
        "--lan_port", type=int, default=None,
        help="UDP port used by the C proxy for peer traffic. Parsed for launch consistency."
    )
    run_parser.add_argument(
        "--remote_port", type=int, default=None,
        help="Remote UDP peer port used by the C proxy. Parsed for launch consistency."
    )
    run_parser.add_argument(
        "--remote_peer_id", type=str, default=None,
        help="Remote peer id used when starting the C proxy in join mode."
    )
    run_parser.add_argument(
        "--peer", action="append", default=[],
        help="Remote peer for the C proxy as peer_id:ip:udp_port. Can be repeated."
    )
    run_parser.add_argument(
        "--spawn_index", type=int, default=None,
        help="Spawn slot for this peer, starting at 0."
    )
    run_parser.add_argument(
        "--spawn_count", type=int, default=3,
        help="Number of spawn slots used to spread online armies."
    )
    run_parser.add_argument(
        "--proxy_path", type=str, default=None,
        help="Path to the compiled C proxy executable."
    )
    run_parser.add_argument(
        "--no_auto_proxy", action="store_true",
        help="Do not start the C proxy automatically from Python."
    )

    # ==================== TestOnline ====================
    run_parser = subparsers.add_parser("testOnline", help="Test online")
    run_parser.add_argument(
        "--ticks", "-t", type=int, default=None,
        help="Maximum ticks to run the battle (omit to run until end)"
    )



    args = parser.parse_args()

    gameMode = None

    def default_proxy_path():
        exe_name = "proxy.exe" if os.name == "nt" else "proxy"
        return os.path.join(os.getcwd(), "network", "src", exe_name)

    def start_proxy_for_online(args, peer_id):
        if args.no_auto_proxy:
            return None

        proxy_path = args.proxy_path or default_proxy_path()
        if not os.path.exists(proxy_path):
            raise FileNotFoundError(
                f"Proxy executable not found: {proxy_path}. "
                "Compile it first or pass --proxy_path."
            )

        lan_port = args.lan_port or 6000
        cmd = [
            proxy_path,
            peer_id,
            str(args.py_port),
            str(lan_port),
        ]

        for peer_spec in args.peer:
            try:
                remote_peer_id, remote_ip, remote_port = peer_spec.rsplit(":", 2)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid --peer value '{peer_spec}'. Expected peer_id:ip:udp_port"
                ) from exc
            cmd.extend([remote_peer_id, remote_ip, str(remote_port)])

        if not args.peer and (args.join or args.remote_port):
            remote_peer_id = args.remote_peer_id or ("player_A" if args.join else "player_B")
            remote_ip = args.join or "127.0.0.1"
            remote_port = args.remote_port or 6000
            cmd.extend([remote_peer_id, remote_ip, str(remote_port)])

        print("[MAIN] Starting C proxy:", " ".join(cmd))
        process = subprocess.Popen(cmd)
        time.sleep(0.5)
        return process

    def mirror_army_positions(army, game_map):
        if not army or not game_map or not hasattr(game_map, "width"):
            return
        for unit in army.units:
            if unit.position is None:
                continue
            x, y = unit.position
            unit.position = (game_map.width - 1 - x, y)

    def spread_army_positions(army, game_map, spawn_index, spawn_count):
        if not army or not game_map or not hasattr(game_map, "width") or not hasattr(game_map, "height"):
            return
        if spawn_index is None:
            return

        positions = [
            (0.12, 0.18),
            (0.82, 0.18),
            (0.47, 0.78),
            (0.12, 0.78),
            (0.82, 0.78),
            (0.47, 0.18),
        ]
        slot = spawn_index % max(1, spawn_count)
        anchor_x_ratio, anchor_y_ratio = positions[slot % len(positions)]

        unit_positions = [unit.position for unit in army.units if unit.position is not None]
        if not unit_positions:
            return

        min_x = min(pos[0] for pos in unit_positions)
        min_y = min(pos[1] for pos in unit_positions)
        target_x = int((game_map.width - 1) * anchor_x_ratio)
        target_y = int((game_map.height - 1) * anchor_y_ratio)
        dx = target_x - min_x
        dy = target_y - min_y

        for unit in army.units:
            if unit.position is None:
                continue
            x, y = unit.position
            unit.position = (
                max(0, min(game_map.width - 1, x + dx)),
                max(0, min(game_map.height - 1, y + dy)),
            )

    def default_spawn_index(args, peer_id):
        if args.spawn_index is not None:
            return args.spawn_index
        if peer_id and peer_id[-1:].isalpha():
            return max(0, ord(peer_id[-1:].upper()) - ord("A"))
        return 1 if args.join else 0

    # ==================== MODE:  ONLINE ====================
    if args.mode == "online":
        peer_id = args.peer_id or ("player_A" if args.create else "player_B")
        proxy_process = start_proxy_for_online(args, peer_id)
        gameMode = Online(peer_id=peer_id, py_port=args.py_port)

        if args.join : gameMode.know_ip.add(args.join)

        print(gameMode.know_ip)

        map_obj = load_map_from_file(args.map_file)
        gameMode.army1 = load_army_from_file(args.army_file)
        if args.peer or args.spawn_index is not None:
            spread_army_positions(
                gameMode.my_army,
                map_obj,
                default_spawn_index(args, peer_id),
                args.spawn_count,
            )
        elif args.join:
            mirror_army_positions(gameMode.my_army, map_obj)

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

        try:
            choice = input("Do you want to save this battle? (y/N): ")
        except EOFError:
            choice = "n"
        if choice.lower().startswith("y"):
            gameMode.isSave = True

        try:
            gameMode.launch()
            gameMode.gameLoop()
        finally:
            gameMode.end()
            if proxy_process is not None and proxy_process.poll() is None:
                proxy_process.terminate()

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

            try:
                choice = input("Do you want to save this battle? (y/N): ")
            except EOFError:
                choice = "n"
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
