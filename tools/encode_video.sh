#!/bin/sh
# Re-encodes a video to the format the Pi's Chromium plays smoothly.
#
# These settings mirror the clips that played reliably on the Pi (H.264
# Main profile, level 4.1, one reference frame, keyframe every second,
# BT.709 tagged, ~15 Mbps cap). High-profile and "fastdecode" encodes
# stalled partway through on the Pi, so don't "optimise" these without
# testing on the real hardware.
#
# Output: 1920x1080, constant 30fps, yuv420p, no audio, with the index
# at the front of the file so playback starts immediately.
#
# Usage: tools/encode_video.sh input.mp4 output.mp4
set -e
ffmpeg -hide_banner -loglevel error -y -i "$1" \
  -an -vf "scale=1920:1080:flags=lanczos,fps=30,format=yuv420p" \
  -c:v libx264 -profile:v main -level 4.1 -preset medium -crf 18 \
  -maxrate 15M -bufsize 15M -refs 1 -g 30 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -movflags +faststart \
  "$2"
