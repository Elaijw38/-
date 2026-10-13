# -*- coding: utf-8 -*-
"""Dump real RGBA values from a reveal layer and recompute the composite by hand.

The algebra said a near-white layer at alpha<=0.55 over a 118 base must land
around 200. The measured result went DOWN. So one of the assumptions is wrong;
this prints the actual bytes so the wrong assumption becomes visible.
"""
import os

import numpy as np
from PIL import Image

OUT = r"C:\DSH\字趣\out"
im = Image.open(os.path.join(OUT, "world-map-reveal-5-life.png"))
a = np.asarray(im)
print("  mode=%s shape=%s dtype=%s" % (im.mode, a.shape, a.dtype))
print("  channel ranges: R %d..%d  G %d..%d  B %d..%d  A %d..%d"
      % (a[..., 0].min(), a[..., 0].max(),
         a[..., 1].min(), a[..., 1].max(),
         a[..., 2].min(), a[..., 2].max(),
         a[..., 3].min(), a[..., 3].max()))

# 取区域核心的一小块，把真实数值打出来
core = a[700:706, 800:806]
print()
print("  sample 6x6 at (800,700)  [R G B A]:")
for row in core:
    print("    " + "  ".join("[%3d %3d %3d %3d]" % tuple(px) for px in row))

base = np.asarray(Image.open(os.path.join(OUT, "world-map.png")).convert("RGB"))
print()
print("  base same spot [R G B]:")
for row in base[700:706, 800:806]:
    print("    " + "  ".join("[%3d %3d %3d]" % tuple(px) for px in row))

# 手工按标准 source-over 算一遍，对照 PIL 的结果
alpha = a[..., 3:4].astype(np.float32) / 255.0
rgb = a[..., :3].astype(np.float32)
bf = base.astype(np.float32)
manual = rgb * alpha + bf * (1.0 - alpha)
print()
print("  manual source-over at same spot:")
for row in manual[700:706, 800:806].astype(np.uint8):
    print("    " + "  ".join("[%3d %3d %3d]" % tuple(px) for px in row))

comp = Image.alpha_composite(Image.open(os.path.join(OUT, "world-map.png")).convert("RGBA"),
                            im).convert("RGB")
ca = np.asarray(comp)
print()
print("  PIL alpha_composite at same spot:")
for row in ca[700:706, 800:806]:
    print("    " + "  ".join("[%3d %3d %3d]" % tuple(px) for px in row))
