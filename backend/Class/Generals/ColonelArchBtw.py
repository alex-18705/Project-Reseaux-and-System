
from backend.Class.Generals.General import General
from backend.Class.Units.Crossbowman import Crossbowman
from backend.Class.Units.Elephant import Elephant
from backend.Class.Units.Knight import Knight
from backend.Class.Units.Monk import Monk
from backend.Class.Units.Pikeman import Pikeman
from backend.Class.Units.Unit import Unit


class ColonelArchBtw(General) :
    def getTargets(self, map, otherArmy):
        deja_pris= set()
        targets=[]
        enemy_units = otherArmy.living_units()
        for unit in self.army.living_units() :
            target = None
            #if unit.last_attacked and unit.last_attacked.is_alive() :
            #    targets.append((unit, unit.last_attacked))
            #else :
            if len(otherArmy.living_units()) > 40 :
                if unit.position is None:
                    continue
                target = min(otherArmy.living_units(), key=lambda enemy: self.__distance_sq(unit, enemy))
                if target is not None:
                    if not isinstance(unit, Monk):
                        targets.append((unit, target))
                    else:
                        if unit.cooldown > 0:
                            allies = [a for a in self.army.living_units() if a.hp < a.max_hp and a != unit]
                            if allies:
                                target = min(allies, key=lambda allie: self.__distance_sq(unit, allie))
                                targets.append((unit, target))
                        else:
                            targets.append((unit, target))

            else:
                if not isinstance(unit, Monk):
                    if isinstance(unit, Crossbowman):
                        pikemans = [e for e in enemy_units if isinstance(e, Pikeman) and e not in deja_pris]
                        target = self.enemy_in_range(unit, pikemans)
                        monks = [e for e in enemy_units if isinstance(e, Monk)]
                        if monks:
                            my_cross = [e for e in self.army.living_units() if isinstance(e, Crossbowman)]
                            proxy_monk = self.enemy_in_range(unit, monks)
                            proxy_cross = self.enemy_in_range(proxy_monk, my_cross)
                            my_cross.remove(proxy_cross)
                            second_cross = self.enemy_in_range(proxy_monk, my_cross)
                            if unit == proxy_cross or unit == second_cross:
                                target = proxy_monk

                    elif isinstance(unit, Pikeman):
                        # elephants = [e for e in enemy_units if isinstance(e, Elephant)]
                        # if elephants :
                        #    target = self.enemy_in_range(unit, elephants)
                        # else :
                        knights = [e for e in enemy_units if isinstance(e, Knight)]
                        target = self.enemy_in_range(unit, knights)
                    elif isinstance(unit, Knight):
                        # my_cross = [e for e in self.army.living_units() if isinstance(e, Crossbowman)]
                        # if self.enemy_in_range(unit, my_cross, 5):
                        #    crossbowmans = [e for e in enemy_units if isinstance(e, Crossbowman)]
                        #    target = self.enemy_in_range(unit, crossbowmans)
                        # else:
                        target = self.enemy_in_range(unit, enemy_units)
                        if isinstance(unit.last_attacker, Pikeman):
                            crossbowmans = [e for e in enemy_units if isinstance(e, Crossbowman)]
                            target = self.enemy_in_range(unit, crossbowmans)
                    elif isinstance(unit, Elephant):
                        my_cross = [e for e in self.army.living_units() if isinstance(e, Crossbowman)]
                        if self.enemy_in_range(unit, my_cross, 3):
                            crossbowmans = [e for e in enemy_units if isinstance(e, Crossbowman)]
                            target = self.enemy_in_range(unit, crossbowmans)
                        else:
                            target = self.enemy_in_range(unit, enemy_units)

                    if target is not None:
                        targets.append((unit, target))
                    else:

                        last_attacker = getattr(unit, "last_attacker", None)
                        if last_attacker in enemy_units:
                            targets.append((unit, last_attacker))
                        else:

                            target = min(
                                enemy_units,
                                key=lambda enemy: self.__distance_sq(unit, enemy),
                                default=None,
                            )
                            if target is not None:
                                targets.append((unit, target))

                else:
                    if unit.cooldown > 40 and unit.last_attacked is not None:

                        if unit.last_attacked is "conversion":
                            unit.last_attacked = max(self.army.living_units(),
                                                     key=lambda allie: self.__distance_sq(unit, allie))
                        target = unit.last_attacked

                        monks = [e for e in enemy_units if isinstance(e, Monk)]
                        if monks:
                            target = self.enemy_in_range(unit, monks)


                    elif unit.cooldown > 0:  # partie heal
                        target = None
                        allies = [a for a in self.army.living_units() if a.hp < a.max_hp - unit.attack and a != unit]
                        if allies:
                            monks = [m for m in allies if isinstance(m, Monk)]
                            if monks: target = self.enemy_in_range(unit, monks, 9)
                            if not target: target = self.enemy_in_range(unit, allies)
                    else:  # partie conversion
                        elephants = [e for e in enemy_units if isinstance(e, Elephant)]
                        if elephants:
                            target = self.enemy_in_range(unit, elephants)
                        else:
                            monks = [e for e in enemy_units if isinstance(e, Monk)]
                            if monks:
                                target = self.enemy_in_range(unit, monks)


                        if not target:
                            target = self.enemy_in_range(unit, enemy_units)

                    if target and isinstance(target, Unit):
                        targets.append((unit, target))
                deja_pris.add(target)

        return targets

    def enemy_in_range(self,unit, enemy_units, range=0):
        if not enemy_units : return None
        target = min(
            enemy_units,
            key=lambda enemy: self.__distance_sq(unit, enemy),
            default=None,
        )
        if not range or (target and self.__distance_sq(unit, target) < range ** 2):
            return target
        return None


    #this function computes the squared distance between two units
    @staticmethod
    def __distance_sq(u1, u2):
        if u1.position is None or u2.position is None:
            return float("inf")
        x1, y1 = u1.position
        x2, y2 = u2.position
        return (x1 - x2) ** 2 + (y1 - y2) ** 2
