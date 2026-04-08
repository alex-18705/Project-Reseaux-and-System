import argparse
import os

from backend.GameModes.Battle import Battle
from backend.GameModes.TestOnline import TestOnline
from backend.Utils.class_by_name import general_from_name, get_available_generals
from backend.Utils.file_loader import load_mirrored_army_from_file, load_map_from_file
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

    # ==================== TestOnline ====================
    run_parser = subparsers.add_parser("testOnline", help="Test online")
    run_parser.add_argument(
        "--ticks", "-t", type=int, default=None,
        help="Maximum ticks to run the battle (omit to run until end)"
    )



    args = parser.parse_args()

    gameMode = None

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
