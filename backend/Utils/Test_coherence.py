

class Test_coherence:

    def __init__(self):
        self.MY_ARMY=None
        self.OTHER_ARMY =None


    def test_coherence(self,my_army, other_army :dict):
        report=[]
        if self.MY_ARMY and my_army :
            report.extend(self.compare_army(self.MY_ARMY, my_army))
        for k in other_army.keys():
            if self.OTHER_ARMY.get(k,None) and other_army.get(k,None) :
                report.extend(self.compare_army(self.OTHER_ARMY[k], other_army[k]))


        self.MY_ARMY = my_army.deepcopy()
        self.OTHER_ARMY = other_army.deepcopy()


        self.print_report(report)

    @staticmethod
    def compare_army(old_army, new_army):
        report =[]
        for unit in new_army.units:
            #collision



            old_unit = old_army.get_unit_by_id(unit.id)
            if old_unit :
                #cooldown
                if unit.hp > old_unit.hp:
                    report.append({"type":"hp", "unit" : unit})
                #degat
                if unit.old_unit.cooldown != 0 and unit.cooldown > old_unit.cooldown:
                    report.append({"type":"cooldown", "unit" : unit})





        return []

    def print_report(self,report):
        pass
