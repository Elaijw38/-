# -*- coding: utf-8 -*-
"""Check the reveal layers: alpha transparency, coverage, and how much each one
actually changes the base map inside its own region.

Three things must be measured, not eyeballed:
  1. Are the corners/edges genuinely transparent? If not, stacking a layer
     would wash out the whole base map.
  2. How much of the frame does each region cover?
  3. How much does one layer shift the base map inside its region?
     Too small -> "cannot tell it has been explored".

Console is GBK, so keep the output ASCII-only.
"""
import os

from PIL import Image, ImageStat

REPO = r"C:\DSH\字趣"
OUT = os.path.join(REPO, "out")
W, H = 1800, 1010

LAYERS = [
    ("1-sky",   "sky"),
    ("2-land",  "land"),
    ("3-plant", "plant"),
    ("4-beast", "beast"),
    ("5-life",  "life"),
]

base = Image.open(os.path.join(OUT, "world-map.png")).convert("RGB")
b0 = ImageStat.Stat(base.convert("L")).mean[0]

print("  base %s  mean luma %.1f" % (base.size, b0))
print()
print("  %-16s %-9s %-10s %-10s %s" % ("layer", "corners", "coverage", "solid", "delta-in-region"))
print("  " + "-" * 70)

ok = True
for fn, name in LAYERS:
    p = os.path.join(OUT, "world-map-reveal-%s.png" % fn)
    im = Image.open(p)
    if im.mode != "RGBA":
        print("  !! %s mode=%s (not RGBA)" % (fn, im.mode))
        ok = False
        continue
    a = im.getchannel("A")
    corners = [a.getpixel(xy) for xy in
               [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1),
                (W // 2, 0), (0, H // 2)]]
    corner_txt = "all-0" if all(c == 0 for c in corners) else ("max %d" % max(corners))
    if max(corners) != 0:
        ok = False
    hist = a.histogram()
    cov = sum(hist[8:]) / float(W * H) * 100.0
    sol = sum(hist[128:]) / float(W * H) * 100.0

    comp = Image.alpha_composite(base.convert("RGBA"), im).convert("RGB")
    mask = a.point(lambda v: 255 if v >= 128 else 0)
    bin_ = ImageStat.Stat(base.convert("L"), mask).mean[0]
    cin = ImageStat.Stat(comp.convert("L"), mask).mean[0]
    print("  %-16s %-9s %-10s %-10s %+.1f  (%.1f -> %.1f)"
          % (fn, corner_txt, "%.1f%%" % cov, "%.1f%%" % sol, cin - bin_, bin_, cin))

allc = base.convert("RGBA")
for fn, _ in LAYERS:
    allc = Image.alpha_composite(
        allc, Image.open(os.path.join(OUT, "world-map-reveal-%s.png" % fn)).convert("RGBA"))
allc = allc.convert("RGB")
print()
print("  all five stacked: %.1f -> %.1f" % (b0, ImageStat.Stat(allc.convert("L")).mean[0]))
print("  corners transparent: %s" % ("PASS" if ok else "FAIL"))
