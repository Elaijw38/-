# -*- coding: utf-8 -*-
"""给地图叠一层带刻度的坐标网格，用来读实物坐标。

图是 2624×1472。网格每 200px 一格，格线上标像素值，
这样看图就能读出某个实物大约是 x=?, y=?，而不是靠猜。

输出：out/_grid/<原名>-grid.jpg
"""
import os

from PIL import Image, ImageDraw, ImageFont

REPO = r"C:\DSH\字趣"
SRC = os.path.join(REPO, "out", "level2-maps")
DST = os.path.join(REPO, "out", "_grid")
os.makedirs(DST, exist_ok=True)

STEP = 200
FONT = None
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(f):
        try:
            FONT = ImageFont.truetype(f, 26)
            break
        except Exception:
            pass

for n in sorted(os.listdir(SRC)):
    if not n.lower().endswith(".jpg"):
        continue
    im = Image.open(os.path.join(SRC, n)).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im, "RGBA")
    for x in range(0, W + 1, STEP):
        d.line([(x, 0), (x, H)], fill=(220, 60, 40, 110), width=1)
        if x:
            d.rectangle([x + 3, 3, x + 78, 34], fill=(20, 16, 12, 190))
            d.text((x + 6, 6), str(x), fill=(255, 220, 170), font=FONT)
    for y in range(0, H + 1, STEP):
        d.line([(0, y), (W, y)], fill=(220, 60, 40, 110), width=1)
        if y:
            d.rectangle([3, y + 3, 78, y + 34], fill=(20, 16, 12, 190))
            d.text((6, y + 6), str(y), fill=(255, 220, 170), font=FONT)
    p = os.path.join(DST, n.replace(".jpg", "-grid.jpg"))
    im.save(p, "JPEG", quality=90, optimize=True)
    print("  %s  %dx%d  每 %dpx 一格" % (p, W, H, STEP))
