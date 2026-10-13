# -*- coding: utf-8 -*-
"""把两个版本的五个分区拼成对照图，便于一眼比较。

上排 = out/minimaps/          页面当前使用的版本（本轮换上的"定向优化"版）
下排 = out/minimaps/_original/ 更早一版备份
"""
import os

from PIL import Image

REPO = r"C:\DSH\字趣"
S = os.path.join(REPO, "out", "minimaps")
O = os.path.join(S, "_original")

NAMES = ["minimap-01-天象.jpg", "minimap-02-山川.jpg", "minimap-03-草木.jpg",
         "minimap-04-禽兽虫鱼.jpg", "minimap-05-人居器物.jpg"]

tw, th = 420, 236
sheet = Image.new("RGB", (tw * 5, th * 2 + 8), (60, 55, 48))
for i, n in enumerate(NAMES):
    a = Image.open(os.path.join(S, n)).convert("RGB").resize((tw, th), Image.LANCZOS)
    b = Image.open(os.path.join(O, n)).convert("RGB").resize((tw, th), Image.LANCZOS)
    sheet.paste(a, (i * tw, 0))
    sheet.paste(b, (i * tw, th + 8))

p = os.path.join(REPO, "out", "_compare-two-versions.jpg")
sheet.save(p, "JPEG", quality=92, optimize=True)
print("  对照图 %s  %dx%d" % (p, sheet.size[0], sheet.size[1]))
print("  上排 = 页面当前版本（out/minimaps/）")
print("  下排 = 更早一版（out/minimaps/_original/）")
