import argparse
import os
import json

from backend.Class.Army import Army
from backend.Utils.file_loader import load_mirrored_army_from_file, load_map_from_file
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Units.Knight import Knight

def main():

        army1, army2 = load_mirrored_army_from_file("./army/classique.army")
        map_obj = load_map_from_file("./map/superflat.map")

        print(army1.units, "\n")
        army_to_json(army1)

UNIT_CLASSES = {
    "Crossbowman": Crossbowman,
    "Knight": Knight,
}

def unit_to_dict(unit):
    return {
        "type": unit.unit_type(),
        "hp": unit.hp,
        "position": unit.position,
        "cooldown": unit.cooldown,
        "last_attacker": unit.last_attacker,
        "last_attacked": unit.last_attacked,
    }

def army_to_json(army):
    data = json.dumps([unit_to_dict(u) for u in army.units])
    with open(f"./army.json", "w") as f:
        f.write(data)
    return data

def json_to_army(filepath="army.json"):
    with open(filepath) as json_file:
        units_data = json.load(json_file)
    army = Army()
    for d in units_data:
        cls = UNIT_CLASSES[d["type"]]
        if cls not in UNIT_CLASSES:
            continue
        unit = cls(
            position=tuple(d["position"] if d["position"] else None),
        )
        unit.hp = d["hp"]
        unit.cooldown = d["cooldown"]
        unit.last_attacker = d["last_attacker"]
        unit.last_attacked = d["last_attacked"]


def map_obj_to_json(map_obj):
    print(map_obj)
    pass
def json_to_map_obj(json):
    pass

"""print(army_to_json(army1))"""
main()

