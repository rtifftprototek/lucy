#!/usr/bin/env python3
"""
Builds lucy-oled-edid.bin: a corrected copy of the EDID reported by the
Kimmybow/Wisecoco 5.5" OLED's HDMI-to-MIPI board.

The board's only mode is 1080x1920@60 with an htotal of 1159 (odd). The
Pi 4's HDMI hardware can't output odd horizontal timings, so the kernel
rejects the mode and the screen goes blank once the display driver
loads. This copy trims the horizontal back porch from 25 to 24 (htotal
1158) and lowers the pixel clock to match, keeping the line rate and the
60Hz refresh the same as the original.
"""

from pathlib import Path

ORIGINAL = """
00 ff ff ff ff ff ff 00 0e d4 32 31 00 88 88 88
20 1c 01 03 80 0c 07 78 0a 0d c9 a0 57 47 98 27
12 48 4c 00 00 00 01 01 01 01 01 01 01 01 01 01
01 01 01 01 01 01 89 34 38 4f 40 80 0e 70 30 06
82 00 38 80 47 00 00 1e 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 fc 00 0a
20 20 20 20 20 20 20 20 20 20 20 20 00 00 00 fc
00 57 69 73 65 63 6f 63 6f 20 20 20 20 20 01 95
02 03 12 f1 23 09 04 01 83 01 00 00 65 03 0c 00
10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 bf
"""

DTD = 0x36  # first detailed timing descriptor in the base block

edid = bytearray.fromhex(ORIGINAL)
assert len(edid) == 256

pixel_clock_10khz = 13437          # was 13449 (134.49 MHz)
h_blank = 48 + 6 + 24              # front + sync + back, was 79
edid[DTD + 0] = pixel_clock_10khz & 0xFF
edid[DTD + 1] = pixel_clock_10khz >> 8
edid[DTD + 3] = h_blank & 0xFF
edid[DTD + 4] = (edid[DTD + 4] & 0xF0) | (h_blank >> 8)

edid[127] = (-sum(edid[:127])) & 0xFF  # base block checksum

out = Path(__file__).parent / "lucy-oled-edid.bin"
out.write_bytes(bytes(edid))
print(f"wrote {out}")
