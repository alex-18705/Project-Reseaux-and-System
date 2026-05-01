import socket
import threading
import time

HOST = "127.0.0.1"
PORT = 5000

def recv_loop(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("[PY] C bridge closed connection")
                break
            print("[PY] Received from C:", data.decode("utf-8"))
        except Exception as e:
            print("[PY] recv error:", e)
            break

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))
print("[PY] Connected to C bridge")

threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()

time.sleep(1)

# giữ chương trình sống để còn nhận message từ C
while True:
    cmd = input("[PY] Enter command (broadcast / sendto / shutdown / quit): ").strip()

    if cmd == "broadcast":
        msg = '{"type":"BROADCAST","payload":{"event":{"kind":"STATE_UPDATE","entity_id":1,"hp":90}}}\n'
        sock.sendall(msg.encode("utf-8"))
        print("[PY] Sent BROADCAST")

    elif cmd == "sendto":
        target_fd = input("target_fd = ").strip()
        msg = (
            '{"type":"SEND_TO","payload":{"target_fd":'
            + target_fd +
            ',"event":{"kind":"CAST_COMMAND","skill":"Q","target_id":99}}}\n'
        )
        sock.sendall(msg.encode("utf-8"))
        print("[PY] Sent SEND_TO")

    elif cmd == "shutdown":
        msg = '{"type":"SHUTDOWN","payload":{}}\n'
        sock.sendall(msg.encode("utf-8"))
        print("[PY] Sent SHUTDOWN")

    elif cmd == "quit":
        break

sock.close()
print("[PY] Closed")