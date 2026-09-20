import cv2
import numpy as np
import os
import random

os.makedirs("data/sample_videos", exist_ok=True)

def create_cctv_video(filename, plate_text="TN87C5106", is_night=False, is_rain=False):
    width, height = 640, 480
    fps = 30
    duration_sec = 4
    total_frames = fps * duration_sec
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_path = os.path.join("data/sample_videos", filename)
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
    
    # Car moves from right to left across camera view
    start_x = width + 100
    end_x = -350
    
    for i in range(total_frames):
        t = i / float(total_frames)
        car_x = int(start_x + t * (end_x - start_x))
        car_y = 180 + int(20 * np.sin(t * np.pi))
        
        # Road / Scene background
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        if not is_night:
            frame[:180, :] = [180, 160, 140] # sky/city
            frame[180:, :] = [60, 60, 65]    # asphalt road
            # Lane markings
            for lx in range(0, width, 90):
                cv2.rectangle(frame, (lx + int(i*2)%90, 320), (lx + 45 + int(i*2)%90, 330), (240, 240, 240), -1)
        else:
            frame[:180, :] = [20, 15, 10]    # night ambient
            frame[180:, :] = [25, 25, 30]    # dark road
            # Streetlight glow
            cv2.circle(frame, (320, 80), 160, (60, 60, 70), -1)

        # Draw Vehicle Body
        cw, ch = 320, 160
        cv2.rectangle(frame, (car_x, car_y), (car_x + cw, car_y + ch), (40, 40, 45) if is_night else (140, 50, 40), -1)
        cv2.rectangle(frame, (car_x + 40, car_y - 50), (car_x + cw - 40, car_y), (30, 30, 35) if is_night else (100, 40, 30), -1)
        # Windows
        cv2.rectangle(frame, (car_x + 55, car_y - 42), (car_x + 140, car_y - 5), (180, 200, 210) if not is_night else (50, 60, 70), -1)
        cv2.rectangle(frame, (car_x + 155, car_y - 42), (car_x + cw - 55, car_y - 5), (180, 200, 210) if not is_night else (50, 60, 70), -1)
        # Wheels
        cv2.circle(frame, (car_x + 70, car_y + ch), 32, (15, 15, 15), -1)
        cv2.circle(frame, (car_x + cw - 70, car_y + ch), 32, (15, 15, 15), -1)

        # Headlights
        if is_night:
            cv2.circle(frame, (car_x + 15, car_y + 60), 16, (255, 255, 240), -1)
            # Beam projection
            pts = np.array([[car_x + 15, car_y + 60], [car_x - 180, car_y + 120], [car_x - 180, car_y - 20]], np.int32)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], (200, 220, 240))
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

        # License Plate on Car
        pw, ph = 140, 42
        px = car_x + 90
        py = car_y + ch - 55
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), (255, 255, 255), -1)
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), (10, 10, 10), 2)
        # Blue IND band
        cv2.rectangle(frame, (px, py), (px + 14, py + ph), (180, 60, 0), -1)
        # Plate characters
        formatted = f"{plate_text[:2]} {plate_text[2:4]} {plate_text[4:]}"
        cv2.putText(frame, formatted, (px + 18, py + 28), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 0, 0), 2)

        # Apply Rain streaks if active
        if is_rain:
            for _ in range(120):
                rx = random.randint(0, width - 1)
                ry = random.randint(0, height - 20)
                cv2.line(frame, (rx, ry), (rx + random.randint(-1, 1), ry + random.randint(8, 18)), (220, 225, 230), 1)

        out.write(frame)

    out.release()
    print(f"[+] Sample CCTV Video created: {out_path}")

create_cctv_video("cctv_daylight_traffic.mp4", "TN87C5106", is_night=False, is_rain=False)
create_cctv_video("cctv_night_rain_traffic.mp4", "OD02AB1234", is_night=True, is_rain=True)
create_cctv_video("cctv_highway_traffic.mp4", "MH12DE1234", is_night=False, is_rain=False)
