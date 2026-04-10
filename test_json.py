import json

from backend.Class.Army import Army
from backend.Class.Map import Map
from backend.Utils.file_loader import load_mirrored_army_from_file, load_map_from_file

from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Monk import Monk
# ... toutes les autres

from backend.Class.Obstacles.Rocher import Rocher



def main():

        army1, army2 = load_mirrored_army_from_file("./army/classique.army")
        map_obj = load_map_from_file("./map/superflat.map")

        print(army1.units, "\n")
        army_to_json(army1)
        print(map_obj.obstacles, "\n")
        map_to_json(map_obj)

        army_end = json_to_army()
        print(army_end.units, "\n")
        json_to_map()
        print(map_obj.obstacles, "\n")


#==============================================
# Transformation des données en dictionnaire  =
#==============================================

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
        "type": obstacle.__class__.__name__,
        "size": obstacle.size,
        "position": obstacle.position,
    }

def map_to_dict(map_obj):
    return {
        "width": map_obj.width,
        "height": map_obj.height,
        "obstacles": [obstacle_to_dict(o) for o in map_obj.obstacles],
    }


#========================
# Conversion de l'armée =
#========================

def army_to_json(army):
    data = json.dumps([unit_to_dict(u) for u in army.units])
    with open(f"./army.json", "w") as f:
        f.write(data)
    return data

def json_to_army():
    filepath = "army.json"
    with open(filepath) as json_file:
        units_data = json.load(json_file)
    army = Army()
    for d in units_data:
        cls = globals().get(d["type"])
        if cls is None:
            continue
        unit = cls(
            position=tuple(d["position"] if d["position"] else None),
        )
        unit.hp = d["hp"]
        unit.cooldown = d["cooldown"]
        unit.last_attacker = d["last_attacker"]
        unit.last_attacked = d["last_attacked"]
        army.units.append(unit)
    return army

#========================
# Conversion de la map  =
#========================

def map_to_json(map_obj):
    data = json.dumps(map_to_dict(map_obj))
    with open(f"./map.json", "w") as f:
        f.write(data)
    return data

def json_to_map():
    filepath = "map.json"
    with open(filepath) as json_file:
        map_data = json.load(json_file)
    
    map_obj=Map(
        width=map_data["width"],
        height=map_data["height"],
    )
    for o in map_data["obstacles"]:
        cls = globals().get(o["type"])
        if cls is None:
            continue
        obs = cls(
            position=tuple(o["position"] if o["position"] else None),
            size=o["size"] if o["size"] else None,
        )
        map_obj.obstacles.add(obs)
    return map_obj

#Appel de main pour contrôler
main()


