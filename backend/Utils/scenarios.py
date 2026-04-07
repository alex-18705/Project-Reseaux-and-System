from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Tuple

from backend.Class.Army import Army
from backend.Class.Map import Map
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Pikeman import Pikeman
from backend.Utils.file_loader import (
    load_map_from_file,
    load_mirrored_army_from_file,
)

ScenarioBuilder = Callable[[], Tuple[Map, Army, Army]]

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent  # backend -> project root


def _asset(path: str) -> str:
    """Return an absolute path inside the project tree."""
    return str(PROJECT_ROOT / path)


def _load_ascii_scenario(army_file: str, map_file: str) -> Tuple[Map, Army, Army]:
    army1, army2 = load_mirrored_army_from_file(_asset(army_file))
    game_map = load_map_from_file(_asset(map_file))
    return game_map, army1, army2


def scenario_classique() -> Tuple[Map, Army, Army]:
    """Baseline scenario pulled from the ASCII files currently in the repo."""
    return _load_ascii_scenario("army/classique.army", "map/superflat.map")


UNIT_TYPES = {
    "knight": Knight,
    "pikeman": Pikeman,
    "crossbowman": Crossbowman,
}


def build_lanchester(
    unit_type: str = "knight",
    n: int = 6,
    width: int = 80,
    height: int = 40,
    spacing: int = 3,
) -> Tuple[Map, Army, Army]:
    """
    Programmatic Lanchester scenario: army1 fields N units, army2 fields 2*N.
    Units spawn within range of one another so casualties line up with Lanchester's law.
    """
    unit_type = unit_type.lower()
    if unit_type not in UNIT_TYPES:
        raise ValueError(f"Unknown unit_type '{unit_type}'. Options: {', '.join(UNIT_TYPES)}")
    cls = UNIT_TYPES[unit_type]

    game_map = Map(width=width, height=height)
    army1 = Army()
    army2 = Army()

    origin_left = width // 3
    origin_right = width - origin_left

    def spawn_line(army: Army, count: int, x_pos: float):
        total_height = (count - 1) * spacing
        start_y = (height - total_height) / 2
        for i in range(count):
            y = start_y + i * spacing
            unit = cls((x_pos, y))
            army.add_unit(unit)

    spawn_line(army1, n, origin_left)
    spawn_line(army2, n * 2, origin_right)
    return game_map, army1, army2


def scenario_lanchester_knights() -> Tuple[Map, Army, Army]:
    return build_lanchester("knight", n=8)


def scenario_lanchester_archers() -> Tuple[Map, Army, Army]:
    return build_lanchester("crossbowman", n=6)


SCENARIO_REGISTRY: Dict[str, ScenarioBuilder] = {
    "classique": scenario_classique,
    "lanchester_knight": scenario_lanchester_knights,
    "lanchester_archer": scenario_lanchester_archers,
}


def register_scenario(name: str, builder: ScenarioBuilder) -> None:
    SCENARIO_REGISTRY[name] = builder


def get_available_scenarios():
    return list(SCENARIO_REGISTRY.keys())


def get_scenario_builder(name: str) -> ScenarioBuilder:
    try:
        return SCENARIO_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown scenario '{name}'. Available: {', '.join(get_available_scenarios())}"
        ) from exc
