# -*- coding: utf-8 -*-
"""导出本轮定稿的两张（大地图、人居器物）并接入页面。

只改这两张：其余四张沿用上一次定稿，不动。
"""
import io
import json
import os
import shutil

from PIL import Image

REPO = r"C:\DSH\字趣"
SRC = r"C:\Users\32058\.dsh\profiles\desktop"
MAPS = os.path.join(REPO, "out", "level2-maps")
ASSETS = os.path.join(REPO, "assets")
W, H = 2624, 1472

# (源文件, out 文件名, assets 文件名)
JOBS = [
    ("task_3HQ2gBimHsJch0XDseCGQuoxXoHyanMX.png",
     "level2-00-world-大地图.jpg", None),
    ("task_31UEmbJE6bRucem7USI49tTJQO5xkZHF.png",
     "level2-05-life-人居器物.jpg", "level2-05-life.jpg"),
]

for src, outname, assetname in JOBS:
    im = Image.open(os.path.join(SRC, src)).convert("RGB")
    sw, sh = im.size
    ar = W / float(H)
    if abs(sw / float(sh) - ar) > 0.01:
        if sw / float(sh) > ar:
            nw = int(round(sh * ar))
            x0 = (sw - nw) // 2
            im = im.crop((x0, 0, x0 + nw, sh))
        else:
            nh = int(round(sw / ar))
            y0 = int(round((sh - nh) / 2))
            im = im.crop((0, y0, sw, y0 + nh))
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    p = os.path.join(MAPS, outname)
    im.save(p, "JPEG", quality=94, optimize=True)
    print("  %-34s %dx%d  %d KB" % (outname, im.size[0], im.size[1],
                                    os.path.getsize(p) // 1024))
    if assetname:
        shutil.copy2(p, os.path.join(ASSETS, assetname))
        print("      -> assets/%s  %d B"
              % (assetname, os.path.getsize(os.path.join(ASSETS, assetname))))

# 确认页面 art 仍指向这两张
obj = json.load(io.open(os.path.join(REPO, "js", "core", "levels.json"), encoding="utf-8"))
print("\n  页面 art 指向：")
for z in obj["map"]["zones"]:
    print("    %-6s %s" % (z["id"], z.get("art")))
