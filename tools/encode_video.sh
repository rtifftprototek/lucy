#!/bin/sh
# Re-encodes a video to the format the Pi's Chromium plays smoothly:
# H.264 (High, yuv420p), constant 30fps, 1920x1080, no audio, with the
# index at the front of the file so playback starts immediately.
# fastdecode + no B-frames keeps decoding cheap for the Pi.
#
# Usage: tools/encode_video.sh input.mp4 output.mp4
set -e
ffmpeg -hide_banner -loglevel error -y -i "$1" \
  -an -vf "scale=1920:1080:flags=lanczos,fps=30,format=yuv420p" \
  -c:v libx264 -profile:v high -level 4.1 -preset slow -crf 18 \
  -tune fastdecode -bf 0 \
  -g 30 -movflags +faststart \
  "$2"
