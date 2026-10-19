# Trade Show Display — Kiosk Starter

Target canvas: **1920 x 1080 landscape**. All sizing in `index.html`
uses viewport-relative units (`vw`/`vh`) rather than hardcoded pixels.

## Display: Kimmybow 5.5" OLED (HDMI-to-MIPI board)

The panel is natively **portrait (1080x1920)**. The kiosk rotates it in
software so the page still renders at 1920x1080 landscape. Two Pi-side
fixes are needed to make it work:

1. **Corrected EDID.**
   - The board reports a single 1080x1920@60 mode with an odd
     horizontal total (1159 px).
   - The Pi 4's HDMI hardware can't output odd horizontal timings, so
     the kernel rejects the mode and the screen goes blank once the
     display driver loads.
   - `display/lucy-oled-edid.bin` is a copy of the board's EDID with
     the back porch trimmed by one pixel. The line rate and refresh
     are unchanged. `display/make_edid.py` regenerates it.

   Install it:
   ```
   sudo mkdir -p /lib/firmware/edid
   sudo cp display/lucy-oled-edid.bin /lib/firmware/edid/
   sudo mount -o remount,rw /boot/firmware
   sudo sed -i '1 s/$/ drm.edid_firmware=HDMI-A-1:edid\/lucy-oled-edid.bin/' /boot/firmware/cmdline.txt
   sudo reboot
   ```
   - `/boot/firmware` is mounted read-only on this Pi, hence the
     remount.
   - `cmdline.txt` must stay a single line.
2. **Rotation.**
   - `kiosk-display.service` runs `wlr-randr` inside `cage` to rotate
     the output by `LUCY_ROTATION` (90; use 270 if the panel is
     mounted the other way).
   - Needs `sudo apt install -y wlr-randr`.

Notes:
- Use the Pi's **HDMI0** port (next to USB-C), which is `HDMI-A-1`.
- Power the panel from its own USB-C supply.
- The boot splash and text before the kiosk starts still look garbled
  or sideways. The firmware stage doesn't use the corrected EDID. This
  is cosmetic only.
- It's an OLED, so use **pure black (`#000000`) backgrounds** and avoid
  bright static elements (burn-in).

## Asset filenames

Drop these into the `assets/` folder next to `index.html`, using these
exact names:

| File | Purpose |
|---|---|
| `eyes_sleeping.mp4` | Sleeping animation — ambient cycle, step 1 |
| `eyes_sleeping_still.png` | Static still image — ambient cycle, step 2 (held for a random duration) |
| `eyes_waking.mp4` | Waking animation — used in both the ambient cycle and the motion sequence |
| `eyes_awake.mp4` | Awake animation — looped a few times, ambient cycle only |
| `eyes_idle.mp4` | Idle animation — motion sequence only |
| `capabilities.mp4` | Capabilities-showcase video |
| `logo.mp4` | Animated logo video |
| `clock_face.png` | Static clock background — numerals, ticks |
| `clock_center.png` | Optional — sits on top of the hands, covering where they meet |
| `clock_hand_hour.png` | Hour hand |
| `clock_hand_minute.png` | Minute hand |
| `clock_hand_second.png` | Optional second hand |

### Hand image spec

Each hand should be exported on a **square transparent canvas, with the
pivot point exactly at the canvas center**, hand pointing straight up
(12 o'clock) from center to wherever its tip should reach. This lets
the code rotate it with a simple CSS `transform: rotate()` around the
image's own center. If the clock face's true center isn't exactly
image-center, tell me the offset and I'll adjust `--clock-cx`/
`--clock-cy` in `index.html`.

### Video export settings

- **Resolution:** exactly 1920x1080, full screen
- **Codec:** H.264 (MP4) — hardware-decoded on the Pi 4B
- **Frame rate:** constant 30fps (not variable)
- Reasonable bitrate (10-20 Mbps is plenty at this resolution)

## Behavior

The display's top-level modes are cycled purely by the physical
button — **no automatic timer** for switching between clock, logo,
animation, and capabilities. Within "animation," the eyes run their
own two-state behavior:

**Sleeping/idle** (the default — repeats forever on its own, with no
motion involved):
1. Plays `eyes_sleeping.mp4` once
2. Holds on the static `eyes_sleeping_still.png` for a random duration (8-20s, configurable via `STILL_HOLD_MIN_MS`/`STILL_HOLD_MAX_MS` near the top of `index.html`'s script)
3. Plays `eyes_waking.mp4` once
4. Plays `eyes_awake.mp4` on repeat a few times (`AWAKE_LOOP_COUNT`, default 3)
5. Back to step 1, indefinitely

**Motion detected** — always interrupts immediately, even mid-sequence, whatever's currently showing (clock, logo, mid-ambient-cycle, anything):
1. Plays `eyes_waking.mp4` once
2. Plays `eyes_idle.mp4` once
3. Re-enters the ambient sleeping/idle cycle from the top

A single press of the mode button advances to the next of the four
modes (clock/logo/animation/capabilities). For bench testing with a
keyboard, press **M** to simulate a motion trigger and **N** to
simulate a button press. Keys **1-4** force a specific mode directly
(1 re-enters the ambient eyes cycle).

## GPIO: mode button + PIR motion sensor

`gpio_control.py` handles both and writes `state.json` as
`{"motionSeq": int, "assetIndex": int, "seq": int}`, which
`index.html` polls twice a second.

**Wiring (BCM pin numbers):**

| Component | Pin | Notes |
|---|---|---|
| Mode button | GPIO17 (physical pin 11) → button → GND | Uses internal pull-up, no resistor needed |
| PIR sensor Signal | GPIO27 (physical pin 13) | SR602 module — power from Pi **3.3V** (pin 1) and GND, no level-shifting needed since it accepts 3.3-15V directly |

Every real motion detection increments `motionSeq`, which the page
treats as "restart the motion sequence from the top" — even if a
previous sequence or the ambient cycle is already mid-playback. There's
no held-awake state or timeout to configure — every motion pulse is
its own independent trigger. (The SR602 has its own ~5s built-in
blocking time between pulses, so this can't fire faster than that
regardless.)

**Install:**
```
sudo apt install -y python3-gpiozero
sudo cp kiosk-gpio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kiosk-gpio
```

**Quick sensor test (bypasses the web page):**
```
sudo systemctl stop kiosk-gpio
python3 -c "from gpiozero import MotionSensor; import time; pir = MotionSensor(27); pir.when_motion = lambda: print('MOTION DETECTED'); print('watching...'); [time.sleep(1) for _ in range(30)]"
sudo systemctl start kiosk-gpio
```

## Raspberry Pi setup (from a clean OS install)

1. **Raspberry Pi OS Lite (64-bit)**, headless-configured via Raspberry
   Pi Imager's advanced options (hostname, SSH, WiFi, username/password)
   so it boots straight to an SSH-reachable state with no monitor/
   keyboard needed.
2. Copy this whole folder to `/home/admin/eve-kiosk` on the Pi (via
   `scp -r . admin@<host>:/home/admin/eve-kiosk/` from your computer).
3. Install packages:
   ```
   sudo apt update
   sudo apt install -y cage chromium seatd python3-gpiozero wlr-randr
   sudo systemctl enable --now seatd
   sudo usermod -aG video admin
   sudo loginctl enable-linger admin
   ```
   Notes:
   - It's the `chromium` package, not `chromium-browser` (that name
     doesn't exist on current Raspberry Pi OS).
   - `seatd` is required — without it, `cage` can't get permission to
     control the display at all and just hangs.
   - The `video` group membership is what grants that permission —
     reboot after this for it to take effect.
   - `loginctl enable-linger` makes systemd create the user session
     (and its `XDG_RUNTIME_DIR`) at boot even with no actual login —
     without this, the kiosk won't start until you SSH in once.
4. Free up tty1, since cage takes it over:
   ```
   sudo systemctl disable getty@tty1.service
   sudo systemctl stop getty@tty1.service
   ```
5. Install the three systemd services:
   ```
   sudo cp kiosk-server.service kiosk-display.service kiosk-gpio.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable kiosk-server kiosk-display kiosk-gpio
   sudo systemctl start kiosk-server kiosk-display kiosk-gpio
   ```
6. Reboot and confirm it comes up on its own with no login required:
   ```
   sudo reboot
   ```

## Known limitation: mouse cursor

A small mouse cursor is visible on screen and there's currently no
clean fix — this is a known, open, unresolved limitation of `cage`
itself (see `cage-kiosk/cage` issue #422 on GitHub), not something our
page's CSS can control if it's actually being drawn by the compositor
rather than the browser. Worth first confirming no USB input device is
plugged into the Pi at all (even briefly, e.g. a keyboard used for
setup) — cage may only draw a cursor when it detects a pointer-capable
seat. Beyond that, there's no guaranteed fix without deeper changes
(input-device filtering tools, or switching compositors) that would
risk destabilizing an otherwise-working setup this close to a show.

## Not yet done

- Read-only root filesystem overlay, to protect the SD card from
  corruption on a hard power cut via the battery toggle switch.
- Final review of `capabilities.mp4`'s content/cut.
