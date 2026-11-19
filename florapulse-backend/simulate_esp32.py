"""FloraPulse ESP32 simulator: one or more sensors, realistic dry-down, obeys pump commands."""
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
DEVICE_KEY = os.getenv("DEVICE_API_KEY", "dev-key-change-me")

UPLOAD_URL = "http://localhost:8000/api/sensor-data/upload"
POLL_INTERVAL = 10
DRY_PER_READING = 0.025     # use 0.2 to rehearse the pump loop quickly
PUMP_BOOST = 30.0
RAIN_PROB = 0.02

SENSORS = sys.argv[1:] or ["ESP32_DEMO_001"]
# each sensor starts at a different moisture so the plants look different
state = {sid: {"m": random.uniform(38, 65), "t": 27.0, "h": 60.0} for sid in SENSORS}


def main():
    headers = {"X-Device-Key": DEVICE_KEY}
    print(f"🌱 Simulating {len(SENSORS)} sensor(s): {', '.join(SENSORS)}")
    print(f"🔑 Device key: {DEVICE_KEY[:4]}…\n")
    n = 0
    while True:
        n += 1
        for sid, s in state.items():
            s["m"] = max(0.0, s["m"] - DRY_PER_READING + random.uniform(-0.05, 0.05))
            s["t"] = min(35, max(18, s["t"] + random.uniform(-0.2, 0.2)))
            s["h"] = min(85, max(30, s["h"] + random.uniform(-0.5, 0.5)))
            rain = random.random() < RAIN_PROB
            payload = {"sensor_id": sid, "moisture": round(s["m"], 1),
                       "temperature": round(s["t"], 1), "humidity": round(s["h"], 1),
                       "rain_detected": rain}
            ts = datetime.now().strftime("%H:%M:%S")
            try:
                r = requests.post(UPLOAD_URL, json=payload, headers=headers, timeout=5)
            except requests.RequestException as e:
                print(f"❌ [{ts}] {sid} backend unreachable: {e}")
                continue
            if r.status_code != 200:
                print(f"❌ [{ts}] {sid} {r.status_code}: {r.text[:100]}")
                continue
            body = r.json()
            pump = body.get("pump", {})
            print(f"✅ [{ts}] #{n} {sid} {payload['moisture']}% | {body.get('decision')} "
                  f"| pump {pump.get('action', 'OFF')}")
            if pump.get("action") == "ON":
                print(f"💧 {sid}: PUMP ON for {pump.get('duration_seconds', 10)}s")
                s["m"] = min(100.0, s["m"] + PUMP_BOOST)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")