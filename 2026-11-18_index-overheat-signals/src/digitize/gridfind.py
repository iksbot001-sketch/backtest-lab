"""Find faint horizontal gridlines: per vertical strip, row-median brightness minima.
usage: gridfind.py img y0 y1 x_list(comma) [halfwidth]"""
import sys
import numpy as np
from PIL import Image
from scipy.signal import find_peaks

img = sys.argv[1]; y0, y1 = int(sys.argv[2]), int(sys.argv[3])
xs = [int(v) for v in sys.argv[4].split(",")]
hw = int(sys.argv[5]) if len(sys.argv) > 5 else 15
a = np.asarray(Image.open(img).convert("L"), dtype=float)
for x in xs:
    strip = a[y0:y1, x - hw:x + hw]
    prof = np.median(strip, axis=1)
    base = np.convolve(prof, np.ones(15) / 15, mode="same")
    dip = base - prof
    pk, pr = find_peaks(dip, prominence=2.0, distance=8)
    out = []
    for p in pk:
        # subpixel centroid
        lo, hi = max(p - 2, 0), min(p + 3, len(dip))
        w = np.clip(dip[lo:hi], 0, None)
        c = (np.arange(lo, hi) * w).sum() / w.sum() if w.sum() > 0 else p
        out.append(f"{y0 + c:.1f}({dip[p]:.0f})")
    print(x, " ".join(out))
