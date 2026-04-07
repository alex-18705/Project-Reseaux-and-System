from backend.Class.Generals.CaptainBraindead import CaptainBraindead
from backend.Class.Generals.ColonelArchBtw import ColonelArchBtw
from backend.Class.Generals.GeneralClever import GeneralClever
from backend.Class.Generals.MajorDaft import MajorDaft
from backend.Class.Units.Castle import Castle
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Units.Elephant import Elephant
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Monk import Monk
from backend.Class.Units.Pikeman import Pikeman

GENERAL_REGISTRY: dict[str, type] = {
            "captainbraindead": CaptainBraindead,
            "majordaft": MajorDaft,
            "generalclever": GeneralClever,
            "colonelarchbtw": ColonelArchBtw,
            "clever" : GeneralClever,
            "daft" : MajorDaft,
        }

@staticmethod
def general_from_name(name: str) :
        return GENERAL_REGISTRY.get(name.lower(), MajorDaft)

@staticmethod
def get_available_generals() :
    return GENERAL_REGISTRY.keys()


UNIT_CLASSES = {
        "knight": Knight,
        "pikeman": Pikeman,
        "crossbowman": Crossbowman,
        "archer": Crossbowman,
        "melee": Knight,
        "castle" : Castle,
        "elephant" : Elephant,
        "monk" : Monk,
        }

@staticmethod
def unit_from_name(name: str):
    return UNIT_CLASSES.get(name.lower())

@staticmethod
def get_available_unit() :
    return UNIT_CLASSES.keys()