
from backend.Class.Generals.General import General
from backend.Class.Units.Monk import Monk


class MajorDaft(General):
    """
    A very aggressive general: every unit rushes head-first toward the closest enemy unit.
    """

    def getTargets(self, map, otherArmy):
        enemies = otherArmy.living_units()
        if not enemies:
            return []

        targets = []
        for unit in self.army.living_units():
            if unit.position is None:
                continue
            target = min(enemies, key=lambda enemy: self.__distance_sq(unit, enemy))
            if target is not None:
                if not isinstance(unit, Monk):
                    targets.append((unit, target))
                else :
                    if unit.cooldown > 0 :
                        allies = [a for a in self.army.living_units() if a.hp < a.max_hp and a != unit]
                        if allies :
                            target = min(allies, key=lambda allie: self.__distance_sq(unit, allie))
                            targets.append((unit, target))
                    else:
                        targets.append((unit, target))
        return targets

    @property
    def name(self):
        return "MajorDaft"

    @staticmethod
    def __distance_sq(u1, u2):
        if u1.position is None or u2.position is None:
            return float("inf")
        x1, y1 = u1.position
        x2, y2 = u2.position
        return (x1 - x2) ** 2 + (y1 - y2) ** 2
