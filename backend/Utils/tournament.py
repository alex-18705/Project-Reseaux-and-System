from __future__ import annotations

import itertools
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from backend.GameModes.Battle import Battle
from backend.Utils.class_by_name import GENERAL_REGISTRY
from backend.Utils.scenarios import (
    SCENARIO_REGISTRY,
    get_available_scenarios,
    get_scenario_builder,
)
from frontend.Affichage import Affichage
from frontend.Terminal.NoAffiche import NoAffiche
from frontend.Terminal.Screen import Screen


@dataclass
class ScoreCounter:
    wins: int = 0
    games: int = 0
    draws: int = 0

    def record(self, win: bool = False, draw: bool = False) -> None:
        self.games += 1
        if draw:
            self.draws += 1
        elif win:
            self.wins += 1

    def pct(self) -> float:
        if self.games == 0:
            return 0.0
        return (self.wins / self.games) * 100.0


@dataclass
class MatchResult:
    scenario: str
    general1_name: str
    general2_name: str
    winner: str
    ticks: int
    army1_survivors: int
    army2_survivors: int

    def summary_line(self) -> str:
        return (
            f"{self.scenario}: {self.general1_name} vs {self.general2_name} -> "
            f"{self.winner} (ticks={self.ticks}, survivors {self.army1_survivors}/{self.army2_survivors})"
        )


@dataclass
class TournamentResult:
    matches: List[MatchResult]
    generals: List[str]
    scenarios: List[str]
    totals: Dict[str, ScoreCounter] = field(default_factory=dict)
    vs_general: Dict[str, Dict[str, ScoreCounter]] = field(default_factory=dict)
    vs_general_per_scenario: Dict[str, Dict[str, Dict[str, ScoreCounter]]] = field(default_factory=dict)
    general_vs_scenario: Dict[str, Dict[str, ScoreCounter]] = field(default_factory=dict)

    def summary_text(self) -> str:
        lines = []
        lines.append("=" * 50)
        lines.append("TOURNAMENT SUMMARY")
        lines.append("=" * 50)
        lines.append(f"Matches: {len(self.matches)}")
        lines.append("")
        lines.append("Overall win rates:")
        for name in self.generals:
            stats = self.totals.get(name)
            if not stats:
                continue
            lines.append(
                f"  {name:>15}: {stats.wins}/{stats.games} wins ({stats.pct():.1f}% | {stats.draws} draw)"
            )
        lines.append("")
        lines.append("Recent matches:")
        for match in self.matches[-5:]:
            lines.append("  " + match.summary_line())
        lines.append("=" * 50)
        return "\n".join(lines)


def _display_factory(headless: bool, use_curses: bool, use_pygame: bool, assets_dir: Optional[str]) -> Affichage:
    if headless:
        return NoAffiche()
    if use_pygame:
        try:
            from frontend.Graphics.PyScreen import PyScreen
            return PyScreen(assets_dir or "frontend/Graphics/pygame_assets/")
        except Exception as exc:
            print(f"Pygame display unavailable ({exc}); falling back to headless mode.")
            return NoAffiche()
    if use_curses:
        return Screen()
    return NoAffiche()


def _compute_stats(
    matches: Sequence[MatchResult],
    generals: Sequence[str],
    scenarios: Sequence[str],
) -> Tuple[
    Dict[str, ScoreCounter],
    Dict[str, Dict[str, ScoreCounter]],
    Dict[str, Dict[str, Dict[str, ScoreCounter]]],
    Dict[str, Dict[str, ScoreCounter]],
]:
    totals = {g: ScoreCounter() for g in generals}
    vs_general = {g: {h: ScoreCounter() for h in generals} for g in generals}
    per_scenario = {
        scenario: {g: {h: ScoreCounter() for h in generals} for g in generals}
        for scenario in scenarios
    }
    general_vs_scenario = {scenario: {g: ScoreCounter() for g in generals} for scenario in scenarios}

    def outcome(row: str, winner: str) -> str:
        if winner == "Draw":
            return "draw"
        if winner == row:
            return "win"
        return "loss"

    for match in matches:
        scenario = match.scenario
        g1 = match.general1_name
        g2 = match.general2_name
        winner = match.winner if match.winner else "Draw"

        for general in (g1, g2):
            if general not in totals:
                totals[general] = ScoreCounter()
            if scenario not in general_vs_scenario:
                general_vs_scenario[scenario] = {general: ScoreCounter()}
            elif general not in general_vs_scenario[scenario]:
                general_vs_scenario[scenario][general] = ScoreCounter()

        outcomes = {
            g1: outcome(g1, winner),
            g2: outcome(g2, winner),
        }

        # overall totals
        for general, result in outcomes.items():
            totals[general].record(win=result == "win", draw=result == "draw")
            general_vs_scenario[scenario][general].record(
                win=result == "win",
                draw=result == "draw",
            )

        # general vs general matrices
        for row, col in ((g1, g2), (g2, g1)):
            row_result = outcomes[row]
            vs_general[row][col].record(win=row_result == "win", draw=row_result == "draw")
            per_scenario[scenario][row][col].record(
                win=row_result == "win",
                draw=row_result == "draw",
            )

    return totals, vs_general, per_scenario, general_vs_scenario


def _determine_winner(battle: Battle, general1_name: str, general2_name: str) -> str:
    army1_empty = battle.army1.isEmpty()
    army2_empty = battle.army2.isEmpty()
    if not army1_empty and army2_empty:
        return general1_name
    if not army2_empty and army1_empty:
        return general2_name
    if battle.max_tick and battle.tick >= battle.max_tick:
        return "Draw"
    if army1_empty and army2_empty:
        return "Draw"
    return "Draw"


def _run_match(
    scenario_name: str,
    general1_name: str,
    general2_name: str,
    *,
    max_ticks: Optional[int],
    delay: float,
    headless: bool,
    use_curses: bool,
    use_pygame: bool,
    assets_dir: Optional[str],
    verbose: bool,
) -> MatchResult:
    builder = get_scenario_builder(scenario_name)
    game_map, army1, army2 = builder()

    general1_cls = GENERAL_REGISTRY[general1_name]
    general2_cls = GENERAL_REGISTRY[general2_name]
    general1 = general1_cls()
    general2 = general2_cls()

    battle = Battle()
    battle.max_tick = max_ticks
    battle.tick_delay = max(0.0, delay)
    battle.frame_delay = 0.0 if headless else battle.frame_delay
    battle.verbose = verbose

    battle.map = game_map
    battle.army1 = army1
    battle.army2 = army2

    army1.general = general1
    army2.general = general2
    general1.army = army1
    general2.army = army2

    affichage = _display_factory(headless, use_curses, use_pygame, assets_dir)
    battle.affichage = affichage

    battle.launch()
    battle.gameLoop()
    battle.end()

    winner = _determine_winner(battle, general1_name, general2_name)
    return MatchResult(
        scenario=scenario_name,
        general1_name=general1_name,
        general2_name=general2_name,
        winner=winner,
        ticks=battle.tick,
        army1_survivors=len(battle.army1.living_units()),
        army2_survivors=len(battle.army2.living_units()),
    )


def run_tournament(
    generals: Optional[Sequence[str]] = None,
    scenarios: Optional[Sequence[str]] = None,
    *,
    repeats: int = 1,
    swap_sides: bool = True,
    delay: float = 0.0,
    max_ticks: Optional[int] = 500,
    use_curses: bool = False,
    use_pygame: bool = False,
    assets_dir: Optional[str] = None,
    headless: bool = True,
    quiet: bool = False,
) -> TournamentResult:
    if generals is None:
        generals = list(GENERAL_REGISTRY.keys())
    if scenarios is None:
        scenarios = list(get_available_scenarios())

    for name in generals:
        if name not in GENERAL_REGISTRY:
            raise ValueError(f"Unknown general '{name}'. Available: {', '.join(GENERAL_REGISTRY)}")

    for scenario in scenarios:
        if scenario not in SCENARIO_REGISTRY:
            raise ValueError(
                f"Unknown scenario '{scenario}'. Available: {', '.join(get_available_scenarios())}"
            )

    matches: List[MatchResult] = []
    total_matchups = len(scenarios) * len(generals) * len(generals) * repeats
    match_index = 0
    for scenario_name in scenarios:
        if not quiet:
            print(f"\n=== Scenario: {scenario_name} ===")
        for g_a, g_b in itertools.product(generals, repeat=2):
            for repeat_idx in range(repeats):
                gen1 = g_a
                gen2 = g_b
                if swap_sides and repeat_idx % 2 == 1:
                    gen1, gen2 = gen2, gen1
                match_index += 1
                if not quiet:
                    print(f"Match {match_index}/{total_matchups}: {gen1} (P1) vs {gen2} (P2)")
                result = _run_match(
                    scenario_name,
                    gen1,
                    gen2,
                    max_ticks=max_ticks,
                    delay=delay,
                    headless=headless,
                    use_curses=use_curses,
                    use_pygame=use_pygame,
                    assets_dir=assets_dir,
                    verbose=not quiet,
                )
                matches.append(result)
                if not quiet:
                    print("  -> " + result.summary_line())

    totals, vs_general, per_scenario, general_vs_scenario = _compute_stats(matches, generals, scenarios)
    return TournamentResult(
        matches=matches,
        generals=list(generals),
        scenarios=list(scenarios),
        totals=totals,
        vs_general=vs_general,
        vs_general_per_scenario=per_scenario,
        general_vs_scenario=general_vs_scenario,
    )


def _format_matrix_row(counter: ScoreCounter) -> str:
    if counter.games == 0:
        return "-"
    return f"{counter.wins}/{counter.games} ({counter.pct():.1f}%)"


def generate_html_report(result: TournamentResult, output_path: str) -> None:
    html = []
    html.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    html.append("<title>Tournament Report</title>")
    html.append(
        "<style>"
        "body{font-family:Arial,sans-serif;background:#f6f6f6;padding:20px;}"
        "table{border-collapse:collapse;margin:18px 0;width:100%;background:white;}"
        "th,td{border:1px solid #ccc;padding:6px 8px;text-align:center;}"
        "th{background:#333;color:#fff;}"
        ".section{margin-top:30px;}"
        "</style>"
    )
    html.append("</head><body>")
    html.append(f"<h1>Tournament Report</h1><p>Generated {datetime.now().isoformat()}</p>")

    html.append("<div class='section'><h2>Overall Scores</h2><table>")
    html.append("<tr><th>General</th><th>Wins</th><th>Games</th><th>Draws</th><th>Win %</th></tr>")
    for name in result.generals:
        stats = result.totals[name]
        html.append(
            f"<tr><td>{name}</td><td>{stats.wins}</td><td>{stats.games}</td>"
            f"<td>{stats.draws}</td><td>{stats.pct():.1f}%</td></tr>"
        )
    html.append("</table></div>")

    def matrix_section(title: str, matrix: Dict[str, Dict[str, ScoreCounter]]):
        html.append(f"<div class='section'><h2>{title}</h2>")
        html.append("<table><tr><th></th>")
        for col in result.generals:
            html.append(f"<th>{col}</th>")
        html.append("</tr>")
        for row in result.generals:
            html.append(f"<tr><th>{row}</th>")
            for col in result.generals:
                cell = matrix[row][col]
                html.append(f"<td>{_format_matrix_row(cell)}</td>")
            html.append("</tr>")
        html.append("</table></div>")

    matrix_section("General vs General (all scenarios)", result.vs_general)

    for scenario in result.scenarios:
        matrix_section(f"General vs General - {scenario}", result.vs_general_per_scenario[scenario])

    html.append("<div class='section'><h2>General vs Scenario</h2>")
    html.append("<table><tr><th>Scenario</th>")
    for general in result.generals:
        html.append(f"<th>{general}</th>")
    html.append("</tr>")
    for scenario in result.scenarios:
        html.append(f"<tr><th>{scenario}</th>")
        for general in result.generals:
            stats = result.general_vs_scenario[scenario][general]
            html.append(f"<td>{_format_matrix_row(stats)}</td>")
        html.append("</tr>")
    html.append("</table></div>")

    html.append("<div class='section'><h2>Match Log</h2>")
    html.append("<table><tr><th>#</th><th>Scenario</th><th>General 1</th><th>General 2</th><th>Winner</th><th>Ticks</th><th>Survivors</th></tr>")
    for idx, match in enumerate(result.matches, 1):
        html.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{match.scenario}</td>"
            f"<td>{match.general1_name}</td>"
            f"<td>{match.general2_name}</td>"
            f"<td>{match.winner}</td>"
            f"<td>{match.ticks}</td>"
            f"<td>{match.army1_survivors}/{match.army2_survivors}</td>"
            "</tr>"
        )
    html.append("</table></div>")
    html.append("</body></html>")

    Path(output_path).write_text("\n".join(html), encoding="utf-8")
    print(f"HTML report written to {output_path}")


def generate_pdf_report(result: TournamentResult, output_path: str) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        print("reportlab not installed, skipping PDF report.")
        return

    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Tournament Report", styles["Title"]),
        Paragraph(f"Generated: {datetime.now().isoformat()}", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    story.append(Paragraph("Overall Win Rates", styles["Heading2"]))
    data = [["General", "Wins", "Games", "Draws", "Win %"]]
    for name in result.generals:
        stats = result.totals[name]
        data.append([name, str(stats.wins), str(stats.games), str(stats.draws), f"{stats.pct():.1f}%"])
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Recent Matches", styles["Heading2"]))
    for match in result.matches[-10:]:
        story.append(Paragraph(match.summary_line(), styles["Normal"]))

    doc.build(story)
    print(f"PDF report written to {output_path}")


def run_tournament_cli(args) -> Optional[TournamentResult]:
    if getattr(args, "list_options", False):
        print("\nAvailable Generals:")
        for name in GENERAL_REGISTRY.keys():
            print(f"  - {name}")
        print("\nAvailable Scenarios:")
        for name in get_available_scenarios():
            print(f"  - {name}")
        return None

    generals = [g.strip() for g in args.generals.split(",")] if args.generals else None
    scenarios = [s.strip() for s in args.scenarios.split(",")] if args.scenarios else None

    result = run_tournament(
        generals=generals,
        scenarios=scenarios,
        repeats=args.repeats,
        swap_sides=not args.no_swap,
        delay=args.delay,
        max_ticks=args.ticks,
        use_curses=args.use_curses and not args.headless,
        use_pygame=args.use_pygame and not args.headless,
        assets_dir=args.assets_dir,
        headless=args.headless or (not args.use_curses and not args.use_pygame),
        quiet=args.quiet,
    )

    print("\n" + result.summary_text())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(getattr(args, "output_dir", "tournament_reports"))
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.html or args.all_reports:
        html_path = output_dir / f"tournament_{timestamp}.html"
        generate_html_report(result, str(html_path))
    if args.pdf or args.all_reports:
        pdf_path = output_dir / f"tournament_{timestamp}.pdf"
        generate_pdf_report(result, str(pdf_path))

    return result
