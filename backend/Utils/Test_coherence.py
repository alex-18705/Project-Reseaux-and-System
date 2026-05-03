from backend.Class.Army import Army
from backend.Utils.convert_json import army_to_dict, json_to_army



class Test_coherence:

    def __init__(self):
        self.MY_ARMY=None
        self.OTHER_ARMY =None




    def test_coherence(self,gamemode):
        report=[]
        if self.MY_ARMY and gamemode.my_army :
            report.extend(self.compare_army(self.MY_ARMY, gamemode.my_army,gamemode.map, gamemode.flat()))
        for k in gamemode.othersArmy.keys():
            if self.OTHER_ARMY and self.OTHER_ARMY.get(k,None) and gamemode.othersArmy.get(k,None) :
                other_list = gamemode.othersArmy.copy()
                del other_list[k]
                other_list["0"] = gamemode.my_army

                otherArmy = Army()
                all_units = []
                for army_id in other_list:
                    all_units.extend(other_list[army_id].units)
                otherArmy.units = all_units

                report.extend(self.compare_army(self.OTHER_ARMY[k], gamemode.othersArmy[k],gamemode.map, otherArmy))

        return report

    def set_armies(self,my_army, othersArmy :dict):
        self.MY_ARMY = json_to_army(army_to_dict(my_army)) if my_army else None
        self.OTHER_ARMY = {
            army_id: json_to_army(army_to_dict(army))
            for army_id, army in othersArmy.items()
            if army is not None
        }

    @staticmethod
    def compare_army(old_army, new_army,map, otherArmy):
        report =[]
        for unit in new_army.units:
            #collision
            if new_army.try_collision(unit,map,unit.position, otherArmy,8) :
                report.append({"type": "collision", "unit": unit})

            old_unit = old_army.get_unit_by_id(unit.id)
            if old_unit :
                # death
                if not old_unit.is_alive() and unit.is_alive():
                    report.append({"type": "zombie", "unit": unit})
                # degat
                if unit.hp > old_unit.hp:
                    report.append({"type":"hp", "unit" : unit})
        return report

    def print_report(self,report):
        for element in report:
            print("Suspicious "+ element["type"] +" from ", element["unit"])
