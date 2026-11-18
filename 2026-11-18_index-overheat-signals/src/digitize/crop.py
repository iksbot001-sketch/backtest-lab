"""Zoomed crop with pixel-coordinate gridlines, for locating control points by eye.
usage: crop.py img x0 y0 x1 y1 out.png [step]"""
import sys
import numpy as np
from PIL import Image, ImageDraw

img, x0, y0, x1, y1, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
step = int(sys.argv[7]) if len(sys.argv) > 7 else 10
im = Image.open(img).convert("RGB").crop((x0, y0, x1, y1))
s = max(1, int(1200 / max(x1 - x0, y1 - y0)))
im = im.resize(((x1 - x0) * s, (y1 - y0) * s), Image.NEAREST)
d = ImageDraw.Draw(im)
for x in range((x0 // step + 1) * step, x1, step):
    c = (255, 0, 0) if x % (step * 5) == 0 else (255, 180, 180)
    d.line([((x - x0) * s, 0), ((x - x0) * s, 6)], fill=c, width=1)
    if x % (step * 5) == 0:
        d.line([((x - x0) * s, 0), ((x - x0) * s, im.height)], fill=(255, 200, 200), width=1)
        d.text(((x - x0) * s + 2, 8), str(x), fill=(255, 0, 0))
for y in range((y0 // step + 1) * step, y1, step):
    c = (0, 0, 255) if y % (step * 5) == 0 else (180, 180, 255)
    d.line([(0, (y - y0) * s), (6, (y - y0) * s)], fill=c, width=1)
    if y % (step * 5) == 0:
        d.line([(0, (y - y0) * s), (im.width, (y - y0) * s)], fill=(200, 200, 255), width=1)
        d.text((8, (y - y0) * s + 2), str(y), fill=(0, 0, 255))
im.save(out)
