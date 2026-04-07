"""
Programmable Lanchester scenarios and dataset generation for plotting.
Provides:
- build_lanchester_scenario(unit_cls, N, general_cls)
- run_lanchester_dataset(...) to collect metrics over ranges and repeats
- helpers to parse CLI expressions (types list, range)
"""
from typing import Iterable, List, Tuple, Type

from backend.Class.Army import Army
from backend.Class.Map import Map
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Generals.MajorDaft import MajorDaft
from backend.Class.Generals.GeneralClever import GeneralClever
from backend.Class.Generals.CaptainBraindead import CaptainBraindead
from backend.Utils.Lanchester.simulation import run_headless_battle
from backend.Utils.class_by_name import general_from_name, unit_from_name


def resolve_general_class(name: str):
    key = (name or "").lower()
    return general_from_name(name.lower())


def parse_types_expr(expr: str) -> List[str]:
    """
    Parse types expression like "[Knight,Crossbow]" -> ["Knight", "Crossbow"]
    """
    text = expr.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        raise ValueError(f"Cannot parse unit types from '{expr}'")
    return parts


def parse_range_expr(expr: str) -> List[int]:
    """
    Parse range expression like "range(1,100)" or "range(1,100,5)".
    Uses Python range semantics (end exclusive).
    """
    text = expr.strip()
    if not text.lower().startswith("range(") or not text.endswith(")"):
        raise ValueError(f"Range must look like range(a,b[,step]), got '{expr}'")
    inside = text[text.find("(") + 1 : -1]
    parts = [p.strip() for p in inside.split(",") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"Range needs at least start and stop, got '{expr}'")
    start = int(parts[0])
    stop = int(parts[1])
    step = int(parts[2]) if len(parts) >= 3 else 1
    return list(range(start, stop, step))


def _make_line_positions(count: int, x: float) -> List[Tuple[float, float]]:
    """
    Place units in a vertical line, spaced by 1 on Y, fixed X.
    """
    return [(x, float(i)) for i in range(count)]


def build_lanchester_scenario(unit_cls: Type, N: int, general_cls: Type) -> Tuple[Map, Army, Army]:
    """
    Build a Lanchester scenario: N vs 2N of the same unit type, within engagement range.
    Units start on adjacent columns so melee can engage immediately and archers are in range.
    """
    # Map sized to fit all units on two columns with some margin
    height = max(10, 2 * N + 2)
    width = max(10, 8)
    game_map = Map(width=width, height=height)

    army1 = Army()
    army2 = Army()

    col_a = 3
    col_b = 4  # adjacent column -> distance 1 (melee can hit), archers definitely in range

    for pos in _make_line_positions(N, col_a):
        army1.add_unit(unit_cls(pos))

    for pos in _make_line_positions(2 * N, col_b):
        army2.add_unit(unit_cls(pos))

    # Assign generals
    gen1 = general_cls()
    gen2 = general_cls()
    army1.general = gen1
    army2.general = gen2
    gen1.army = army1
    gen2.army = army2

    # Attach gameMode map-like reference if needed for clamping
    army1.gameMode = type("GM", (), {"map": game_map})()
    army2.gameMode = army1.gameMode

    return game_map, army1, army2


def _initial_hp(army: Army) -> int:
    return sum(u.hp for u in army.units)


def run_lanchester_dataset(
    unit_names: Iterable[str],
    N_values: Iterable[int],
    general_cls,
    repeats: int = 10,
    max_ticks: int = 500,
):
    """
    Run Lanchester(type, N) for each unit type and N in range, repeated `repeats` times.
    Returns a list of aggregated rows:
      {
        "unit_type": "<name>",
        "N": <int>,
        "winner": "Army1"|"Army2"|"Draw",
        "casualties_winner": <float, avg over repeats>,
        "ticks_avg": <float>,
      }
    Casualties are computed for the winning side (so we can plot how costly the win is).
    """
    rows = []
    for unit_name in unit_names:
        cls = unit_from_name(unit_name.lower())
        if cls is None:
            raise ValueError(f"Unknown unit type '{unit_name}'")
        for N in N_values:
            cas_winner_list = []
            tick_list = []
            win_labels = []
            for _ in range(repeats):
                game_map, army1, army2 = build_lanchester_scenario(cls, N, general_cls)

                init_hp1 = _initial_hp(army1)
                init_hp2 = _initial_hp(army2)
                init_cnt1 = len(army1.units)
                init_cnt2 = len(army2.units)

                result = run_headless_battle(game_map, army1, army2, max_ticks=max_ticks)

                surv1 = result["army1_survivors"]
                surv2 = result["army2_survivors"]
                hp1 = result["army1_hp_remaining"]
                hp2 = result["army2_hp_remaining"]
                tick_list.append(result["ticks"])

                if surv1 > 0 and surv2 == 0:
                    winner = "Army1"
                    casualties = init_cnt1 - surv1
                    hp_lost = init_hp1 - hp1
                elif surv2 > 0 and surv1 == 0:
                    winner = "Army2"
                    casualties = init_cnt2 - surv2
                    hp_lost = init_hp2 - hp2
                else:
                    winner = "Draw"
                    # In draw, take the smaller casualties (best surviving side) to plot conservatively
                    casualties = min(init_cnt1 - surv1, init_cnt2 - surv2)
                    hp_lost = min(init_hp1 - hp1, init_hp2 - hp2)

                # Prioritize casualty count; hp_lost could be used by other plotters
                cas_winner_list.append(casualties)
                win_labels.append(winner)

            avg_cas = sum(cas_winner_list) / len(cas_winner_list)
            avg_ticks = sum(tick_list) / len(tick_list)
            # majority winner (simple mode)
            winner_majority = max(set(win_labels), key=win_labels.count)

            rows.append({
                "unit_type": unit_name,
                "N": N,
                "winner": winner_majority,
                "casualties_winner": avg_cas,
                "ticks_avg": avg_ticks,
            })
    return sorted(rows, key=lambda r: (r["unit_type"], r["N"]))