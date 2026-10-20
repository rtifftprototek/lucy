#!/usr/bin/env python3
"""
Raw PIR sensor diagnostic - shows exactly how often the sensor itself
fires, with zero cooldown/gating applied (bypasses gpio_control.py
entirely). Useful for understanding the sensor's real hardware
behavior/sensitivity independent of any of the app's own logic.

Usage:
    sudo systemctl stop kiosk-gpio   # frees the sensor pin for this script to use
    python3 test_pir.py
    (Ctrl+C to stop)
    sudo systemctl start kiosk-gpio  # resume normal operation after
"""

import time
from gpiozero import MotionSensor

PIR_PIN = 22  # BCM number = physical pin 15 - keep in sync with gpio_control.py

pir = MotionSensor(PIR_PIN)
last_time = None
count = 0


def on_motion():
    global last_time, count
    count += 1
    now = time.time()
    if last_time is None:
        print(f"[{count}] MOTION (first detection)")
    else:
        print(f"[{count}] MOTION - {now - last_time:.1f}s since last")
    last_time = now


pir.when_motion = on_motion

print(f"Watching raw PIR sensor output on GPIO{PIR_PIN}. Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print(f"\nStopped. {count} total detections.")
