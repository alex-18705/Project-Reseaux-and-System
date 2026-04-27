How to Test (Local 1v1)

### Terminal 1 (Host - Blue)
```powershell
.\.venv\Scripts\python.exe main.py online --create --general MajorDaft --army_file army/two.army --map_file map/superflat.map --pygame --py_port 5000 --lan_port 6000 --remote_port 6001
```

### Terminal 2 (Client - Red)
```powershell
.\.venv\Scripts\python.exe main.py online --join 127.0.0.1 --general MajorDaft --army_file army/two.army --map_file map/superflat.map --pygame --py_port 5001 --lan_port 6001 --remote_port 6000
```

## 4. Key Networking Ports

