# Lucy — Robot Dog / Trade Show Display

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
   - `kiosk-display.service` starts `kiosk-start.sh` inside `cage`. The
     script runs `wlr-randr` to rotate the output by `LUCY_ROTATION`
     (90; use 270 if the panel is mounted the other way), retrying
     until the output is ready, then starts Chromium.
   - Needs `sudo apt install -y wlr-randr`.

Notes:
- Use the Pi's **HDMI0** port (next to USB-C), which is `HDMI-A-1`.
- Power the panel from its own USB-C supply.
- The boot splash and text before the kiosk starts still look garbled
  or sideways. The firmware stage doesn't use the corrected EDID. This
  is cosmetic only.
- It's an OLED, so use **pure black (`#000000`) backgrounds** and avoid
  bright static elements (burn-in).

## Assets

Everything the display plays lives in `assets/`:

| File | Used for |
|---|---|
| `dog/wake_up.mp4` | Plays once whenever Lucy wakes up |
| `dog/idle_loop.mp4` | Main awake animation (40s) |
| `dog/look_around.mp4` | Awake action |
| `dog/perk_up.mp4` | Awake action |
| `dog/fall_asleep.mp4` | Plays once when she goes back to sleep |
| `dog/sleeping_loop.mp4` | Loops the whole time she's asleep |
| `sign/welcome_animation.mp4` | FABTECH welcome animation, plays once |
| `sign/prototek_1.mp4` | Prototek motion logo, plays once |
| `sign/prototek_2.mp4` | Prototek certifications & registrations, plays once |
| `sign/welcome_slide.png` | Welcome slide, held after the animation (the animation ends on this exact image) |
| `clock/clock_face.png` | Clock numerals, 1920x1080 on black |
| `clock/clock_hand_hour.png`, `clock_hand_minute.png` | Clock hands |
| `clock/clock_center.png` | "P" cap over the middle of the hands |
| `clock/clock_hand_second.png` | Optional second hand; hidden if the file is missing |

`source_assets/` holds the designer's original exports. The dog clips
there are MPEG-4 Part 2, which Chromium can't play, so the versions in
`assets/dog/` are re-encoded copies. Convert any new videos the same way:

```
tools/encode_video.sh input.mp4 assets/dog/new_clip.mp4
```

### Asset spec (for the designer)

- **Canvas:** 1920x1080 landscape, **pure black (`#000000`)
  background**. It's an OLED, so avoid bright elements that sit still
  for long periods (burn-in).
- **Video:** MP4, H.264, yuv420p, constant 30fps, no audio.
- **Seamless joins:** every awake clip starts and ends on the same
  "neutral open eyes" frame, so they can be mixed in any order.
  Looping clips end on their first frame.
- **Filenames:** lowercase, no spaces.
- **Clock hands and cap:** transparent square PNGs, pivot at the exact
  center, pointing straight up (12 o'clock).

## Behavior

There are two modes. The **button toggles between them**, and the
display boots into dog mode.

### Dog mode (Lucy)

1. **Wakes up.** `wake_up` plays once.
2. **Awake period** (random 45–90s, `AWAKE_MIN_MS`/`AWAKE_MAX_MS`):
   - plays a random mix of the idle loop, look around and perk up
     (`AWAKE_ACTIONS`, with weights)
   - the idle loop always plays at least once
   - the same clip never plays twice in a row
3. **Falls asleep.** `fall_asleep` plays once.
4. **Sleeps.** `sleeping_loop` repeats for a random 3–8 minutes
   (`SLEEP_MIN_MS`/`SLEEP_MAX_MS`), then she wakes on her own (back to
   step 1).

**Motion** wakes her straight away (back to step 1), but only while
she's asleep and has been for at least 10s
(`MIN_SLEEP_BEFORE_MOTION_MS`). Motion while she's awake, or while
she's falling asleep, is ignored.

### Digital sign mode

Cycles forever through `SIGN_PLAYLIST`:
1. **Clock** for 30s, in Pacific time (`CLOCK_TIME_ZONE`), whatever the Pi's own time zone.
2. **Prototek motion logo** (`prototek_1.mp4`, 8.5s).
3. **FABTECH welcome:** the animation plays, then the slide holds for
   20s.
4. **Prototek certifications & registrations** (`prototek_2.mp4`, 20s).

- A `video` entry whose file is missing is skipped automatically.
- Motion is ignored in this mode.
- To add another video, convert it with `tools/encode_video.sh` into
  `assets/sign/` and add a `{ type: 'video', src: ... }` entry to
  `SIGN_PLAYLIST`.

### Other

- All timings are constants at the top of the script in `index.html`.
- The whole picture drifts a few pixels every 2 minutes to spread OLED
  wear (`DRIFT_*`).

**Bench-testing keys** (with a keyboard plugged in):

| Key | Does |
|---|---|
| N | Same as a button press |
| M | Simulate motion |
| D | Dog mode |
| S | Sign mode |
| W | Wake Lucy now |

## GPIO: mode button + PIR motion sensor

`gpio_control.py` handles both and writes `state.json` as
`{"motionSeq": int, "assetIndex": int, "seq": int}`, which
`index.html` polls twice a second.

**Wiring (BCM pin numbers):**

| Component | Pin | Notes |
|---|---|---|
| Mode button | GPIO17 (physical pin 11) → button → GND | Uses internal pull-up, no resistor needed |
| PIR sensor Signal | GPIO22 (physical pin 15) | SR602 module — power from Pi **3.3V** (pin 1) and GND (e.g. pin 9), no level-shifting needed since it accepts 3.3-15V directly. Moved from GPIO27/pin 13, which stopped reading the sensor; `PIR_PIN` in `gpio_control.py` and `test_pir.py` |

- A button press increments `seq`, and the page switches mode.
- A motion detection increments `motionSeq`, and the page may wake
  Lucy (see Behavior).
- `gpio_control.py` ignores triggers less than 5s apart, and the SR602
  has its own ~5s blocking time too.

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
python3 -c "from gpiozero import MotionSensor; import time; pir = MotionSensor(22); pir.when_motion = lambda: print('MOTION DETECTED'); print('watching...'); [time.sleep(1) for _ in range(30)]"
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

## Updating the Pi

The Pi's copy lives in `/home/admin/eve-kiosk`.

**First time:** turn that folder into a git checkout of this branch, so
later updates are one command. This keeps the old folder as a backup.

```
sudo apt install -y git
cd /home/admin
mv eve-kiosk eve-kiosk.bak
git clone -b claude/zealous-gauss-geyx21 https://github.com/rtifftprototek/lucy.git eve-kiosk
sudo systemctl restart kiosk-server kiosk-gpio kiosk-display
```

**After that:**

```
cd /home/admin/eve-kiosk && git pull && sudo systemctl restart kiosk-server kiosk-gpio kiosk-display
```

If a `.service` file changed, also copy it into `/etc/systemd/system/`
and run `sudo systemctl daemon-reload` before restarting.

**Watching what the page is doing:** the page's log messages (clips
starting, motion, watchdog skips) go to the server's log:

```
journalctl -u kiosk-server -f
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
- More Prototek logo animations for sign mode, once delivered.
