import json

from backend.Class.Army import Army
from backend.Utils.file_loader import load_mirrored_army_from_file, load_map_from_file


def main():

        army1, army2 = load_mirrored_army_from_file("./army/classique.army")
        map_obj = load_map_from_file("./map/superflat.map")

        print(army1.units, "\n")
        army_to_json(army1)
        print(map_obj.obstacles, "\n")
        map_to_json(map_obj)


def unit_to_dict(unit):
    return {
        "type": unit.__class__.__name__,
        "hp": unit.hp,
        "position": unit.position,
        "cooldown": unit.cooldown,
        "last_attacker": unit.last_attacker_id,
        "last_attacked": unit.last_attacked_id,
    }

def obstacle_to_dict(obstacle):
    return {
        "size": obstacle.size,
        "position": obstacle.position,
    }

def map_to_dict(map):
    return {
        "width": map.width,
        "height": map.height,
        "obstacles": [obstacle_to_dict(o) for o in map.obstacles],
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
        cls = d["type"]
        cls_name= globals()[cls]
        if cls not in cls_name:
            continue
        unit = cls(
            position=tuple(d["position"] if d["position"] else None),
        )
        unit.hp = d["hp"]
        unit.cooldown = d["cooldown"]
        unit.last_attacker = d["last_attacker"]
        unit.last_attacked = d["last_attacked"]


def map_to_json(map_obj):
    data = json.dumps(map_to_dict(map_obj))
    with open(f"./map.json", "w") as f:
        f.write(data)
    return data

def json_to_map(json):
    pass

#Appel de main pour contrôler
main()


