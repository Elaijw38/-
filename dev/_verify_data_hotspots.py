# -*- coding: utf-8 -*-
"""按**写进数据里的真实坐标与半径**画热区，并检查重叠。

与 _verify_hotspots.py 的区别：那个画的是"清单文件"，
这个画的是**数据文件里最终生效的值**，才是网页真正会用的东西。

同时按项目既有的自检口径检查热区重叠：
圆心距 < 半径和 * 0.75 就报（两个热区叠一起会点不准）。
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

REPO = r"C:\DSH\字趣"
ASSETS = os.path.join(REPO, "assets")
DST = os.path.join(REPO, "out", "_verify")
os.makedirs(DST, exist_ok=True)

obj = json.load(io.open(os.path.join(REPO, "js", "core", "levels.json"), encoding="utf-8"))

FONT = None
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(f):
        try:
            FONT = ImageFont.truetype(f, 38)
            break
        except Exception:
            pass

print("  %-8s %-10s %s" % ("区", "物件", "热区重叠"))
print("  " + "-" * 46)
for z in obj["map"]["zones"]:
    zid = z["id"]
    art = z.get("art")
    if not art:
        continue
    p = os.path.join(REPO, art.replace("/", os.sep))
    if not os.path.exists(p):
        print("  !! 缺图 %s" % p)
        continue
    im = Image.open(p).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    # 重叠检查
    os_ = z["objects"]
    bad = []
    for i in range(len(os_)):
        for j in range(i + 1, len(os_)):
            a, b = os_[i], os_[j]
            dist = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
            if dist < (a["r"] + b["r"]) * 0.75:
                bad.append("%s/%s(%.0f<%.0f)" % (a["char"], b["char"], dist,
                                                 (a["r"] + b["r"]) * 0.75))
    for o in os_:
        x, y, r = o["x"], o["y"], o["r"]
        d.ellipse([x - r, y - r, x + r, y + r], outline=(240, 70, 45, 255), width=4)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(240, 70, 45, 255))
        tx, ty = x - 18, y - r - 44
        d.rectangle([tx - 4, ty - 2, tx + 46, ty + 42], fill=(18, 14, 10, 210))
        d.text((tx, ty), o["char"], fill=(255, 228, 186), font=FONT)
    op = os.path.join(DST, "data-%s-%s-marks.jpg" % (zid, z["name"]))
    im.save(op, "JPEG", quality=90, optimize=True)
    print("  %-8s %-10s %s" % (zid, "%d 个" % len(os_),
                               ("、".join(bad) if bad else "无")))
print("\n  叠图目录 %s" % DST)
