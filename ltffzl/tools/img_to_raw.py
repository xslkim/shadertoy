"""Convert any image into the host's bg.raw format.

  python img_to_raw.py <input_image> <output.raw> [size]

Center-crops to a square, resizes to size x size (default 1024), and writes
8-byte header (int32 w, int32 h, little-endian) + RGB24 data.
"""
import sys
import struct
from PIL import Image

inp = sys.argv[1]
out = sys.argv[2]
S = int(sys.argv[3]) if len(sys.argv) > 3 else 1024

im = Image.open(inp).convert("RGB")
w, h = im.size
side = min(w, h)
left = (w - side) // 2
top = (h - side) // 2
im = im.crop((left, top, left + side, top + side)).resize((S, S), Image.LANCZOS)

with open(out, "wb") as f:
    f.write(struct.pack("<ii", S, S))
    f.write(im.tobytes())

print(f"wrote {out}  {S}x{S}  (from {w}x{h})")
