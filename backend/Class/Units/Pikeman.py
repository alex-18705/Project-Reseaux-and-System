from backend.Class.Units.Unit import Unit


class Pikeman(Unit):


    def __init__(self, position: tuple[float]):
        super().__init__(55, attack=4, armor=0,
                         speed=1, range_=1, reload_time=3,ligne_of_sight=6, position=position, classes=["Infantry", "Spear"], bonuses={"Cavalry": 10})

    def unit_type(self) -> str:
        return "Pikeman"

