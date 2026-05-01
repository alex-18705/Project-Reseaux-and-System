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
        proxy_cmd = ["../src/proxy.exe", "5001", "9001", "127.0.0.1", "9000"]
    )
    bridge.connect()

    print(f"[REMOTE] Waiting for forwarded message from C proxy at {host}:{port}...")

    deadline = time.time() + 30
    replied = False

    try:
        while time.time() < deadline:
            updates = bridge.get_updates()
            for msg in updates:
                print("[REMOTE] Received:", msg)
                if not replied:
                    bridge.send_message(
                        "TEST_FROM_REMOTE",
                        {
                            "sender": "python-remote",
                            "text": "reply from remote python",
                        },
                    )
                    print("[REMOTE] Reply sent.")
                    replied = True
            if replied:
                time.sleep(2.0)
                break
            time.sleep(0.1)
    finally:
        bridge.disconnect()
        print("[REMOTE] Stopped.")


if __name__ == "__main__":
    main()
