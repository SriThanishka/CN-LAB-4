import socket, struct, cv2, time, math

# ---------------- CONFIG ----------------
SERVER_IP = "0.0.0.0"   # bind to all interfaces
SERVER_PORT = 9999
VIDEO_PATH = "video1.mp4"   # put your video file name here, or 0 for webcam
CHUNK_SIZE = 8192
JPEG_QUALITY = 80
HDR_STRUCT = "!IHHB"
HDR_SIZE = struct.calcsize(HDR_STRUCT)
# ----------------------------------------

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"[SERVER] Listening on {(SERVER_IP, SERVER_PORT)}... waiting for client START")

    # wait for client
    while True:
        data, client_addr = sock.recvfrom(1024)
        if data.decode(errors="ignore").strip().upper() == "START":
            print(f"[SERVER] Got START from {client_addr}. Streaming begins...")
            break

    # open video
    cap = cv2.VideoCapture(0 if VIDEO_PATH == "0" else VIDEO_PATH)
    if not cap.isOpened():
        print("[SERVER] ERROR: cannot open video source:", VIDEO_PATH)
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = 1.0 / fps
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]

    frame_no = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[SERVER] End of video")
                break

            result, enc = cv2.imencode(".jpg", frame, encode_param)
            if not result:
                continue
            bdata = enc.tobytes()
            total_packets = math.ceil(len(bdata) / CHUNK_SIZE)

            for seq in range(total_packets):
                start = seq * CHUNK_SIZE
                chunk = bdata[start:start + CHUNK_SIZE]
                marker = 1 if seq == (total_packets - 1) else 0
                hdr = struct.pack(HDR_STRUCT, frame_no, seq, total_packets, marker)
                sock.sendto(hdr + chunk, client_addr)

            if frame_no % 30 == 0:
                print(f"[SERVER] Sent frame {frame_no}, {len(bdata)} bytes, {total_packets} packets")

            frame_no += 1
            time.sleep(frame_interval)
    except KeyboardInterrupt:
        print("[SERVER] Stopped by user")
    finally:
        for _ in range(3):
            sock.sendto(b"END", client_addr)
        cap.release()
        sock.close()
        print("[SERVER] Closed")

if __name__ == "_main_":
    main()