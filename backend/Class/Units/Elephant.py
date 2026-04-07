from backend.Class.Units.Unit import Unit


class Elephant(Unit):
    def __init__(self, position: tuple[float]):
        super().__init__(300, attack=14, armor=2,
                         speed=1, range_=1, reload_time=2, ligne_of_sight=8,position=position,size=2, classes=["Cavalry"], bonuses={"Castle": 7})

    def unit_type(self) -> str:
        return "Elephant"