

import jsonpickle

from backend.Class.Units.Knight import Knight
from backend.Utils.file_loader import load_mirrored_army_from_file

army1, army2 = load_mirrored_army_from_file("./army/classique.army")

a= Knight((0,0))



json_data = jsonpickle.dumps(a)

b = jsonpickle.loads(json_data)

print(json_data)
print(a,b, a==b)
