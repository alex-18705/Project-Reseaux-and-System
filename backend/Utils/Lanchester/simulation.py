"""
Headless battle runner for fast, non-visual simulations (e.g., Lanchester experiments).
"""

from typing import Dict

from backend.Class.Army import Army
from backend.Class.Map import Map


def run_headless_battle(game_map: Map, army1: Army, army2: Army, max_ticks: int = 500) -> Dict[str, int]:
    """
    Run a minimal, headless battle loop until one army is dead or max_ticks reached.
    Returns survivors and remaining HP for both armies.
    """
    tick = 0
    while tick < max_ticks and not army1.isEmpty() and not army2.isEmpty():
        army1.fight(game_map, otherArmy=army2)
        army2.fight(game_map, otherArmy=army1)
        tick += 1

    return {
        "army1_survivors": len(army1.living_units()),
        "army2_survivors": len(army2.living_units()),
        "army1_hp_remaining": sum(u.hp for u in army1.living_units()),
        "army2_hp_remaining": sum(u.hp for u in army2.living_units()),
        "ticks": tick,
    }