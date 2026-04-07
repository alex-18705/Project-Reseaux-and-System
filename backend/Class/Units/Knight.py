from backend.Class.Units.Unit import Unit


class Knight(Unit):
    def __init__(self, position: tuple[float]):
        super().__init__(100, attack=10, armor=2,
                         speed=2, range_=1, reload_time=2, ligne_of_sight=4,position=position, classes=["Cavalry"], bonuses={"Infantry": 2})

    def unit_type(self) -> str:
        return "Knight"
