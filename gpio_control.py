#!/usr/bin/env python3
"""
Trade show display - GPIO control

Purely button-driven mode switching (no automatic timer) combined with
motion-triggered eye animation. Any real motion detection immediately
interrupts whatever's showing and runs the eyes' motion sequence in the
web page (waking -> idle -> back into the ambient sleeping/idle cycle) -
but only if at least MIN_MOTION_INTERVAL_SECONDS has passed since the
last accepted trigger, so continuous nearby motion (e.g. someone
fidgeting right next to the sensor during bench testing) doesn't
restart the sequence on every single pulse.

This script writes {motionSeq, assetIndex, seq} to state.json.
`motionSeq` increments on every ACCEPTED motion detection (i.e. one
that passed the cooldown check) - the SR602 itself also has its own
~5s built-in blocking time between raw pulses, so the two together
mean triggers are spaced at least MIN_MOTION_INTERVAL_SECONDS apart in
practice. `assetIndex` is which of the four main modes should show
right now; `seq` increments on every button press. index.html polls
this file twice a second and reacts to either counter changing. All
the actual eye-clip chaining/timing lives in that JS.

Wiring (BCM numbering):
  Mode button : GPIO17 -> button -> GND       (uses internal pull-up)
  PIR sensor  : GPIO27 <- SR602 signal pin    (SR602 powered from 3.3V + GND)

Run as a systemd service (see kiosk-gpio.service) so it starts on boot
and restarts automatically if it ever crashes.
"""

import json
import time
from pathlib import Path
from gpiozero import Button, MotionSensor

STATE_FILE = Path(__file__).parent / "state.json"

ROTATION_LENGTH = 4  # MAIN_MODES length in index.html - keep in sync
MIN_MOTION_INTERVAL_SECONDS = 5  # ignore new triggers faster than this

mode_button = Button(17, pull_up=True, bounce_time=0.05)
pir = MotionSensor(27)

state = {
    "motionSeq": 0,
    "assetIndex": 0,
    "seq": 0,
}
last_motion_trigger_time = 0.0


def write_state():
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(STATE_FILE)  # atomic, so the page never reads a half-written file


def force_next_mode():
    state["assetIndex"] = (state["assetIndex"] + 1) % ROTATION_LENGTH
    state["seq"] += 1
    print(f"[button] -> assetIndex {state['assetIndex']}")
    write_state()


def on_motion():
    global last_motion_trigger_time
    now = time.time()
    if now - last_motion_trigger_time < MIN_MOTION_INTERVAL_SECONDS:
        print(f"[motion] ignored (cooldown, {now - last_motion_trigger_time:.1f}s since last)")
        return
    last_motion_trigger_time = now
    state["motionSeq"] += 1
    print(f"[motion] -> motionSeq {state['motionSeq']}")
    write_state()


mode_button.when_pressed = force_next_mode
pir.when_motion = on_motion

write_state()  # write initial state immediately on startup
print("Ready. Waiting for button presses / motion...")

try:
    from signal import pause
    pause()
except KeyboardInterrupt:
    pass
