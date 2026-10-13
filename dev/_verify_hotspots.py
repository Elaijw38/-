# -*- coding: utf-8 -*-
"""把 hotspots.json 的标记画到图上，自查坐标是否落在实物上。

这是必要的自查：清单是我看图读出来的，必须**画回去验证**，
否则给网页的坐标就是废纸。
输出：out/_verify/<图名>-marks.jpg
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

REPO = r"C:\DSH\字趣"
SRC = os.path.join(REPO, "out", "level2-maps")
DST = os.path.join(REPO, "out", "_verify")
os.makedirs(DST, exist_ok=True)

data = json.load(io.open(os.path.join(SRC, "hotspots.json"), encoding="utf-8"))

FONT = None
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(f):
        try:
            FONT = ImageFont.truetype(f, 40)
            SMALL = ImageFont.truetype(f, 34)
            break
        except Exception:
            pass

for key, items in data.items():
    if not items:
        continue
    import glob
    cand = glob.glob(os.path.join(SRC, "level2-%s-*.jpg" % key))
    if not cand:
        print("  !! 找不到 %s 的图" % key)
        continue
    p = cand[0]
    im = Image.open(p).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    for it in items:
        x, y = it["x"], it["y"]
        r = 46
        d.ellipse([x - r, y - r, x + r, y + r],
                  outline=(230, 60, 40, 255), width=5)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(230, 60, 40, 255))
        tx, ty = x + r + 6, y - 26
        d.rectangle([tx - 4, ty - 4, tx + 62, ty + 50], fill=(18, 14, 10, 205))
        d.text((tx, ty), it["char"], fill=(255, 226, 180), font=FONT)
    op = os.path.join(DST, os.path.basename(p).replace(".jpg", "-marks.jpg"))
    im.save(op, "JPEG", quality=90, optimize=True)
    print("  %s  %d 个标记" % (op, len(items)))
