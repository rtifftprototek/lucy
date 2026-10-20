#!/bin/sh
# Runs inside cage (see kiosk-display.service): rotates the display, then
# starts Chromium.
#
# The 5.5" OLED panel is natively portrait (1080x1920), so the output is
# rotated to give the page a 1920x1080 landscape canvas.
#
# A one-off rotation isn't enough: right after cage starts its output
# isn't always ready, and the screen can later reset itself to portrait
# (e.g. if the HDMI-to-MIPI board briefly drops and reconnects). So a
# background loop checks every couple of seconds and re-applies the
# rotation whenever it's been lost. systemd stops it along with cage.
ROTATION="${LUCY_ROTATION:-90}"
OUTPUT=HDMI-A-1

(
  while true; do
    if ! wlr-randr 2>/dev/null | grep -q "Transform: $ROTATION"; then
      if wlr-randr --output "$OUTPUT" --transform "$ROTATION" 2>/dev/null; then
        echo "kiosk-start: rotated $OUTPUT to $ROTATION"
      fi
    fi
    sleep 2
  done
) &

exec /usr/bin/chromium \
  --kiosk \
  --ozone-platform=wayland \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-translate \
  --no-first-run \
  --overscroll-history-navigation=0 \
  --autoplay-policy=no-user-gesture-required \
  --check-for-update-interval=31536000 \
  http://localhost:8080/index.html
