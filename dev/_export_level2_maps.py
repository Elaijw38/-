# -*- coding: utf-8 -*-
"""导出六张第二关地图原图（独立 16:9，不加任何东西）。

严格只做：等比裁到 16:9 → 存为 JPEG。
**不加水印、不加标题、不加边框、不拼图、不叠任何文字。**

同时输出六张的缩略预览（仅用于一眼对照风格，不是交付物的一部分）。
"""
import os

from PIL import Image

REPO = r"C:\DSH\字趣"
SRC = r"C:\Users\32058\.dsh\profiles\desktop"
DST = os.path.join(REPO, "out", "level2-maps")
os.makedirs(DST, exist_ok=True)

W, H = 2624, 1472

MAPS = [
    ("00-world",    "大地图",     "task_ZW7siujwltM75YGEMPIWaPc5JCMUshMl.png"),
    ("01-sky",      "天象",       "task_AX8VVDcZayDurFLU2JR2oF5oIOlYbsEh.png"),
    ("02-land",     "山川",       "task_NRp5BXQ4yWi3wWrFUExLQChFU1YLLU7u.png"),
    ("03-plant",    "草木",       "task_QaxeJrLXkqBWgGmtmT2QAgzvVzIWIwJW.png"),
    ("04-beast",    "禽兽虫鱼",   "task_O3B4R28hLbKdNUU8Vhzw935vkG0iNfR8.png"),
    ("05-life",     "人居器物",   "task_Pew1Tycct7sBkjDQP2l9VsqECau8xP9s.png"),
]

print("  %-12s %-10s %-11s %s" % ("文件", "主题", "尺寸", "大小"))
print("  " + "-" * 52)

thumbs = []
for tag, name, fn in MAPS:
    im = Image.open(os.path.join(SRC, fn)).convert("RGB")
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
    p = os.path.join(DST, "level2-%s-%s.jpg" % (tag, name))
    im.save(p, "JPEG", quality=94, optimize=True)
    print("  %-12s %-10s %-11s %d KB"
          % ("level2-%s" % tag, name, "%dx%d" % im.size,
             os.path.getsize(p) // 1024))
    thumbs.append(im)

# 缩略对照（仅自查用，不是交付物）
tw, th = 430, 241
sheet = Image.new("RGB", (tw * 6, th), (242, 232, 213))
for i, im in enumerate(thumbs):
    sheet.paste(im.resize((tw, th), Image.LANCZOS), (i * tw, 0))
p = os.path.join(REPO, "out", "_level2-6up-check.jpg")
sheet.save(p, "JPEG", quality=92, optimize=True)
print("\n  六张缩略对照（仅自查，非交付物）%s" % p)
print("  交付目录 %s" % DST)
