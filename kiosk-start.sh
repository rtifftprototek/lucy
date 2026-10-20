#!/bin/sh
# Runs inside cage (see kiosk-display.service): rotates the display, then
# starts Chromium.
#
# The 5.5" OLED panel is natively portrait (1080x1920), so the output is
# rotated to give the page a 1920x1080 landscape canvas. Right after cage
# starts, its output isn't always ready yet and wlr-randr fails, which
# left the screen in portrait - so keep retrying for up to ~10s.
ROTATION="${LUCY_ROTATION:-90}"
tries=0
until wlr-randr --output HDMI-A-1 --transform "$ROTATION"; do
  tries=$((tries + 1))
  if [ "$tries" -ge 50 ]; then
    echo "kiosk-start: could not rotate the display" >&2
    break
  fi
  sleep 0.2
done

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
