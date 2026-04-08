import argparse
import os

from backend.GameModes.Battle import Battle
from backend.Utils.class_by_name import general_from_name, get_available_generals
from backend.Utils.file_loader import load_mirrored_army_from_file, load_map_from_file
from backend.Utils.Lanchester.lanchester import (
    run_lanchester_dataset,
    parse_range_expr,
    parse_types_expr,
    resolve_general_class,
)
from backend.Utils.plotters import plot_lanchester
from backend.Utils.scenarios import get_available_scenarios
from backend.Utils.tournament import run_tournament_cli
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

    # ==================== PLOT (Lanchester, programmable) ====================
    plot_parser = subparsers.add_parser(
        "plot",
        help="battle plot <AI> <plotter> <scenario(arg1,...)> <range for arg1> ... [-N=repeat]"
    )
    plot_parser.add_argument("ai", type=str, help="AI/general name (e.g., DAFT, CLEVER, BRAINDEAD)")
    plot_parser.add_argument("plotter", type=str, help="Plotter name (e.g., PlotLanchester)")
    plot_parser.add_argument("scenario", type=str, help="Scenario name (currently: Lanchester)")
    plot_parser.add_argument("types_expr", type=str,
                             help="Unit types list, e.g., [Knight,Crossbow]")
    plot_parser.add_argument("range_expr", type=str,
                             help='Range expression for N, e.g., range(1,100) or range(1,100,5)')
    plot_parser.add_argument(
        "--repeat", "-N", type=int, default=10,
        help="Number of repeats per (type, N) run (default: 10)"
    )
    plot_parser.add_argument(
        "--max-ticks", "-t", type=int, default=500,
        help="Maximum ticks per simulation (default: 500)"
    )
    plot_parser.add_argument(
        "--graph", "-g", dest="graph_path", type=str, default="lanchester.png",
        help="Output path for the PNG graph (default: lanchester.png)"
    )
    plot_parser.add_argument(
        "--no-graph", action="store_true",
        help="Disable graph generation"
    )

    # ==================== TOURNAMENT ====================
    tournament_parser = subparsers.add_parser("tournament", help="Run an automated tournament")
    tournament_parser.add_argument(
        "--generals", "-g", type=str, default=None,
        help="Comma-separated list of generals (default: all available)"
    )
    tournament_parser.add_argument(
        "--scenarios", "-s", type=str, default=None,
        help=f"Comma-separated list of scenarios (available: {', '.join(get_available_scenarios())})"
    )
    tournament_parser.add_argument(
        "--repeats", "-r", type=int, default=3,
        help="Number of repeats per matchup (default: 3)"
    )
    tournament_parser.add_argument(
        "--no-swap", action="store_true",
        help="Disable side swapping between repeats"
    )
    tournament_parser.add_argument(
        "--delay", "-d", type=float, default=0.0,
        help="Seconds between ticks (default: 0 for fastest)"
    )
    tournament_parser.add_argument(
        "--ticks", "-t", type=int, default=500,
        help="Maximum ticks per match (default: 500)"
    )
    tournament_parser.add_argument(
        "--curses", action="store_true", dest="use_curses",
        help="Use the curses terminal display"
    )
    tournament_parser.add_argument(
        "--pygame", action="store_true", dest="use_pygame",
        help="Use the pygame graphical display"
    )
    tournament_parser.add_argument(
        "--assets-dir", type=str, default="frontend/Graphics/pygame_assets",
        help="Directory containing pygame assets"
    )
    tournament_parser.add_argument(
        "--headless", action="store_true",
        help="Force headless mode (NoAffiche display)"
    )
    tournament_parser.add_argument(
        "--output-dir", "-o", type=str, default="tournament_reports",
        help="Directory where tournament reports will be stored"
    )
    tournament_parser.add_argument(
        "--html", action="store_true",
        help="Generate an HTML report"
    )
    tournament_parser.add_argument(
        "--pdf", action="store_true",
        help="Generate a PDF report (requires reportlab)"
    )
    tournament_parser.add_argument(
        "--all-reports", action="store_true",
        help="Generate both HTML and PDF reports"
    )
    tournament_parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress per-match logs"
    )
    tournament_parser.add_argument(
        "--list", action="store_true", dest="list_options",
        help="List available generals and scenarios and exit"
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

    # ==================== MODE: PLOT (Lanchester laws) ====================
    elif args.mode == "plot":
        scenario_name = args.scenario.lower()
        if scenario_name != "lanchester":
            print(f"Unsupported scenario '{args.scenario}'. Only 'Lanchester' is available.")
            return

        unit_names = parse_types_expr(args.types_expr)
        N_values = parse_range_expr(args.range_expr)
        general_cls = resolve_general_class(args.ai)

        dataset = run_lanchester_dataset(
            unit_names=unit_names,
            N_values=N_values,
            general_cls=general_cls,
            repeats=args.repeat,
            max_ticks=args.max_ticks,
        )

        print("\nLanchester plot dataset (averaged per (type, N)):")
        for row in dataset:
            print(
                f"type={row['unit_type']:>9} | N={row['N']:>4} | "
                f"winner={row['winner']:>8} | "
                f"casualties_winner={row['casualties_winner']:>4} | "
                f"ticks_avg={row['ticks_avg']:.2f}"
            )

        graph_path = None
        if not args.no_graph:
            graph_path = plot_lanchester(dataset, args.graph_path)
            if graph_path:
                print(f"\nGraph saved to: {graph_path}")
            else:
                print("\nGraph generation skipped (matplotlib not installed).")
        else:
            print("\nGraph generation disabled (--no-graph).")
    # ==================== MODE: TOURNAMENT ====================
    elif args.mode == "tournament":
        run_tournament_cli(args)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
