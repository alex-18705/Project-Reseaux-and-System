from backend.Class.Army import Army
from backend.Class.Generals.General import General
from backend.Class.Map import Map
from backend.Class.Units.Monk import Monk


class CaptainBraindead(General):
    """
    Units retaliate against their last attacker; if nobody hit them yet, they just
    pick the closest visible enemy (simple nearest-neighbour heuristic).
    """

    def getTargets(self, map: Map, otherArmy: Army):
        targets = []
        enemy_units = otherArmy.living_units()
        if not enemy_units: #this is to prevent errors when there are no enemy units alive
            return targets

        for unit in self.army.living_units():

            last_attacker = getattr(unit, "last_attacker", None)
            if last_attacker in enemy_units:
                targets.append((unit, last_attacker))
            else :

            # no recent attacker: engage closest enemy in line of sight (simplified to nearest distance)
                target = min(
                    enemy_units,
                    key=lambda enemy: self.__distance_sq(unit, enemy),
                    default=None,
                )
                if target is not None:
                    if not isinstance(unit, Monk):
                        if self.__distance_sq(unit, target) < unit.line_of_sight ** 2:
                            targets.append((unit, target))
                    else :
                        if unit.cooldown > 0 :
                            allies = [a for a in self.army.living_units() if a.hp < a.max_hp and a != unit]
                            if allies :
                                target = min(allies, key=lambda allie: self.__distance_sq(unit, allie))
                                if self.__distance_sq(unit, target) < unit.line_of_sight ** 2:
                                    targets.append((unit, target))
                        else :
                            if self.__distance_sq(unit, target) < unit.line_of_sight ** 2:
                                targets.append((unit, target))
        return targets

    #this function computes the squared distance between two units
    @staticmethod
    def __distance_sq(u1, u2):
        if u1.position is None or u2.position is None:
            return float("inf")
        x1, y1 = u1.position
        x2, y2 = u2.position
        return (x1 - x2) ** 2 + (y1 - y2) ** 2
