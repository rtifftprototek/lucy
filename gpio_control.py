#!/usr/bin/env python3
"""
Trade show display - GPIO control

The mode button toggles the web page between dog mode and digital sign
mode. The PIR sensor reports motion, which can wake Lucy when she's
asleep in dog mode (index.html decides whether a given motion counts).
Motion triggers less than MIN_MOTION_INTERVAL_SECONDS apart are dropped,
so continuous nearby motion (e.g. someone fidgeting right next to the
sensor during bench testing) doesn't flood the page.

This script writes {motionSeq, assetIndex, seq, motionActive} to
state.json. `motionActive` is true for as long as the sensor's output is
high (it stays high while motion continues), so the page can wake Lucy
for someone who's already standing there, not just on a fresh trigger.
`motionSeq` increments on every ACCEPTED motion detection (i.e. one
that passed the cooldown check) - the SR602 itself also has its own
~5s built-in blocking time between raw pulses. `seq` increments on
every button press; `assetIndex` tracks which of the two modes should
be showing. index.html polls this file twice a second and reacts to
either counter changing. All the actual clip chaining/timing lives in
that JS.

Wiring (BCM numbering):
  Mode button : GPIO27 (pin 13) -> button -> GND   (uses internal pull-up)
  PIR sensor  : GPIO22 (pin 15) <- SR602 signal    (SR602 powered from 3.3V + GND)

Run as a systemd service (see kiosk-gpio.service) so it starts on boot
and restarts automatically if it ever crashes.
"""

import json
import time
from pathlib import Path
from gpiozero import Button, MotionSensor

STATE_FILE = Path(__file__).parent / "state.json"

ROTATION_LENGTH = 2  # MODES length in index.html (dog, sign) - keep in sync
MIN_MOTION_INTERVAL_SECONDS = 5  # ignore new triggers faster than this
BUTTON_PIN = 27  # BCM number = physical pin 13
PIR_PIN = 22  # BCM number = physical pin 15

mode_button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.05)
pir = MotionSensor(PIR_PIN)

state = {
    "motionSeq": 0,
    "assetIndex": 0,
    "seq": 0,
    "motionActive": False,
}
last_motion_trigger_time = 0.0


def write_state():
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(STATE_FILE)  # atomic, so the page never reads a half-written file


def force_next_mode():
    state["assetIndex"] = (state["assetIndex"] + 1) % ROTATION_LENGTH
    state["seq"] += 1
    print(f"[button] -> assetIndex {state['assetIndex']}", flush=True)
    write_state()


def on_motion():
    global last_motion_trigger_time
    state["motionActive"] = True
    now = time.time()
    if now - last_motion_trigger_time < MIN_MOTION_INTERVAL_SECONDS:
        print(f"[motion] active (cooldown, {now - last_motion_trigger_time:.1f}s since last trigger)", flush=True)
    else:
        last_motion_trigger_time = now
        state["motionSeq"] += 1
        print(f"[motion] -> motionSeq {state['motionSeq']}", flush=True)
    write_state()


def on_no_motion():
    state["motionActive"] = False
    print("[motion] cleared", flush=True)
    write_state()


mode_button.when_pressed = force_next_mode
pir.when_motion = on_motion
pir.when_no_motion = on_no_motion

write_state()  # write initial state immediately on startup
print("Ready. Waiting for button presses / motion...", flush=True)

try:
    from signal import pause
    pause()
except KeyboardInterrupt:
    pass
