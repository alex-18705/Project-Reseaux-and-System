# Project Status & Requirements Check

## 1. Feature Integration (Thanh branch)
- **Camera Controls**: Mouse drag to move camera, scroll to zoom.
- **Minimap**: 2.5D Isometric minimap with click-to-teleport functionality.
- **Centering**: Press 'C' to center the camera on the battlefield.
- **UI Localization**: Integrated localized French UI and statistics panel (F1-F4).
- **Animations**: Smooth unit movement interpolation.

## 2. Requirements Check (IAS 25-26 Repartition)
| Requirement | Status | Implementation Detail |
| :--- | :--- | :--- |
| **Create Online Game** | ✅ Complete | `Online.py` gamemode implemented. |
| **Mimic AoE2** | ✅ Complete | RTS-style combat, AI control, and isometric view. |
| **2 Players (2 PCs/Terminals)** | ✅ Complete | P2P architecture using `proxy_udp.c`. |
| **Control an AI** | ✅ Complete | Players select a General (AI) to control their army. |
| **Real-time Sync** | ✅ Complete | State-broadcasting model with non-blocking loops. |
| **Automated Proxy** | ✅ Complete | `NetworkBridge` starts `proxy_udp.exe` automatically. |

## 3. How to Test (Local 1v1)

### Terminal 1 (Host - Blue)
```powershell
.\.venv\Scripts\python.exe main.py online --create --general MajorDaft --army_file army/two.army --map_file map/superflat.map --pygame --py_port 5000 --lan_port 6000 --remote_port 6001
```

### Terminal 2 (Client - Red)
```powershell
.\.venv\Scripts\python.exe main.py online --join 127.0.0.1 --general MajorDaft --army_file army/two.army --map_file map/superflat.map --pygame --py_port 5001 --lan_port 6001 --remote_port 6000
```

## 4. Key Networking Ports
- **py_port**: Internal communication between Python and C Proxy.
- **lan_port**: Port used to listen for network packets.
- **remote_port**: The `lan_port` of the other player.
