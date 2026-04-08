import struct

FORMAT = "<iiiffi"
pipe_path = "/tmp/c_to_py"

print("Python: Attente de données de C...")
with open(pipe_path, "rb") as f:
    data = f.read(struct.calcsize(FORMAT))
    res = struct.unpack(FORMAT, data)
    print(f"Python reçu de C: ID={res[0]}, HP={res[5]}")