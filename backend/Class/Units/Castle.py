from backend.Class.Units.Unit import Unit


class Castle(Unit):
    def __init__(self, position: tuple[float]):
        super().__init__(4800, attack=55, armor=9,
                         speed=0, range_=8, reload_time=2, ligne_of_sight=11,position=position,size=5, classes=["Castle"], bonuses={})

    def unit_type(self) -> str:
        return "Castle"
