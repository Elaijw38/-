# -*- coding: utf-8 -*-
"""Where exactly is the alpha nonzero near the border? Print a coarse map.

The corner check reports a scalar per sample point; that does not say whether
the leak is a thin rim, a genuine blob touching an edge, or a stray artifact.
This prints the alpha value on a coarse grid so the shape is visible as text.
"""
import os

import numpy as np
from PIL import Image

OUT = r"C:\DSH\字趣\out"
W, H = 1800, 1010

for fn in ("1-sky", "2-land", "3-plant", "4-beast", "5-life"):
    a = np.asarray(Image.open(os.path.join(OUT, "world-map-reveal-%s.png" % fn))
                   .convert("RGBA").getchannel("A"), dtype=np.uint8)
    print("=== %s ===" % fn)
    # 每 101 像素取一行/列，打印alpha的两位十六进制（00 = 全透明）
    step_y, step_x = H // 10, W // 18
    for y in range(0, H, step_y):
        row = []
        for x in range(0, W, step_x):
            row.append("%02x" % a[y, x])
        print("  y%4d %s" % (y, " ".join(row)))
    # 边缘带统计
    band = 6
    edges = {
        "top": a[:band, :], "bottom": a[-band:, :],
        "left": a[:, :band], "right": a[:, -band:],
    }
    txt = "  ".join("%s max=%d n>0=%d" % (k, v.max(), int((v > 0).sum()))
                    for k, v in edges.items())
    print("  " + txt)
    print()
