#!/usr/bin/env python3
"""
UDP Video Streaming Client (with resize so video fits window)
Press 'q' to quit
"""

import socket, struct, cv2, numpy as np, time

# ---------------- CONFIG ----------------
SERVER_IP = "10.21.16.179"   # IP of the server machine
SERVER_PORT = 9999
CLIENT_IP = "0.0.0.0"        # bind to all local interfaces
CLIENT_PORT = 10000
SOCKET_TIMEOUT = 0.5
FRAME_TIMEOUT = 3.0
RESIZE_WIDTH = 200         # resize display width
RESIZE_HEIGHT = 740          # resize display height
HDR_STRUCT = "!IHHB"
HDR_SIZE = struct.calcsize(HDR_STRUCT)
# ----------------------------------------

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((CLIENT_IP, CLIENT_PORT))
    sock.settimeout(SOCKET_TIMEOUT)
    print(f"[CLIENT] Bound to {(CLIENT_IP, CLIENT_PORT)}")

    # send START to server
    sock.sendto(b"START", (SERVER_IP, SERVER_PORT))
    print(f"[CLIENT] Sent START to {(SERVER_IP, SERVER_PORT)}")

    frames = {}

    # allow window resizing
    cv2.namedWindow("UDP Video Client", cv2.WINDOW_NORMAL)

    try:
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                # drop old frames
                now = time.time()
                to_delete = []
                for fno, meta in frames.items():
                    if now - meta["first_ts"] > FRAME_TIMEOUT:
                        to_delete.append(fno)
                for fno in to_delete:
                    del frames[fno]
                continue

            if data == b"END":
                print("[CLIENT] Stream ended by server")
                break

            if len(data) < HDR_SIZE:
                continue

            frame_no, seq_no, total_packets, marker = struct.unpack(HDR_STRUCT, data[:HDR_SIZE])
            payload = data[HDR_SIZE:]

            if frame_no not in frames:
                frames[frame_no] = {"chunks": {}, "total": total_packets, "first_ts": time.time()}
            frames[frame_no]["chunks"][seq_no] = payload

            if len(frames[frame_no]["chunks"]) == frames[frame_no]["total"]:
                try:
                    payload = b"".join(frames[frame_no]["chunks"][i] for i in range(frames[frame_no]["total"]))
                except KeyError:
                    del frames[frame_no]
                    continue

                arr = np.frombuffer(payload, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    # 🔹 Resize video before showing
                    frame_resized = cv2.resize(frame, (RESIZE_WIDTH, RESIZE_HEIGHT))
                    cv2.imshow("UDP Video Client", frame_resized)

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("[CLIENT] Quit requested by user")
                        break
                del frames[frame_no]

    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        cv2.destroyAllWindows()
        print("[CLIENT] Closed")

if __name__ == "__main__":
    main()