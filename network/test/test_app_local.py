import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.network_api import NetworkBridge


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

    bridge = NetworkBridge(
        host=host, 
        port=port,
        auto_start = True,
        proxy_cmd = ["../src/proxy.exe", "5000", "9000", "127.0.0.1", "9001"]
    )
    bridge.connect()

    time.sleep(3.0)

    print(f"[LOCAL] Sending test message to C proxy at {host}:{port}...")
    bridge.send_message(
        "TEST_FROM_LOCAL",
        {
            "sender": "python-local",
            "text": "hello from local python",
        },
    )

    deadline = time.time() + 15
    try:
        while time.time() < deadline:
            updates = bridge.get_updates()
            for msg in updates:
                print("[LOCAL] Received:", msg)
            time.sleep(0.1)
    finally:
        bridge.disconnect()
        print("[LOCAL] Stopped.")


if __name__ == "__main__":
    main()
