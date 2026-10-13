# -*- coding: utf-8 -*-
"""Stack metrics with several alpha thresholds.

The earlier check used alpha>8 to define "inside", which drags in the entire
feather halo (most of the frame) including dark terrain, so the reported
"inside" average was dominated by non-revealed pixels. Print several
thresholds and also restrict to fully-solid pixels, which is the only set
where the claim "revealed areas get brighter" can be tested cleanly.
"""
import os

import numpy as np
from PIL import Image

OUT = r"C:\DSH\字趣\out"
W, H = 1800, 1010
NAMES = ["1-sky", "2-land", "3-plant", "4-beast", "5-life"]

base = Image.open(os.path.join(OUT, "world-map.png")).convert("RGB")
L = [Image.open(os.path.join(OUT, "world-map-reveal-%s.png" % n)).convert("RGBA") for n in NAMES]

comp = base.convert("RGBA")
for im in L:
    comp = Image.alpha_composite(comp, im)
comp = comp.convert("RGB")

bm = np.asarray(base.convert("L"), dtype=np.float32)
cm = np.asarray(comp.convert("L"), dtype=np.float32)

amax = np.zeros((H, W), dtype=np.uint8)
for im in L:
    amax = np.maximum(amax, np.asarray(im.getchannel("A")))

print("  alpha histogram (max across the five layers):")
tot = float(W * H)
for lo, hi in ((0, 0), (1, 32), (33, 64), (65, 128), (129, 200), (201, 255)):
    n = int(((amax >= lo) & (amax <= hi)).sum())
    print("    %3d..%-3d  %8d px  %5.2f%%" % (lo, hi, n, n / tot * 100))

print()
print("  %-14s %-8s %-9s %-9s %s" % ("threshold", "px", "base", "stacked", "delta"))
print("  " + "-" * 56)
for th in (8, 32, 64, 128, 200):
    m = amax >= th
    if m.sum() == 0:
        continue
    b, c = bm[m].mean(), cm[m].mean()
    print("  alpha>=%-7d %-8d %-9.1f %-9.1f %+.1f" % (th, int(m.sum()), b, c, c - b))

m = ~(amax > 0)
print()
print("  untouched (alpha==0): %d px (%.1f%%)  base %.1f -> stacked %.1f"
      % (int(m.sum()), m.mean() * 100, bm[m].mean(), cm[m].mean()))
