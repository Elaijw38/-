# -*- coding: utf-8 -*-
"""第二关：带**源图像素刻度**的放大镜。用于精确读目标物中心坐标。

用法：
  python dev/_l2_measure.py beast 0.0 0.0 0.5 0.5          # 归一化四角，输出带网格的放大块
  python dev/_l2_measure.py beast 0 0 1312 736             # 也可直接给源图像素四角
  python dev/_l2_measure.py beast 0.0 0.0 0.5 0.5 1200     # 指定输出宽

网格：每格 = STEP 源图像素（按视野自动选 50/100/200），标签写源图 x / y。
图中还会画出该区**现有热点**（红圈+字名）与**候选点**（蓝十字），便于对照。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(REPO, "js", "core", "levels.json")
OUT = os.path.join(REPO, "out", "l2-measure")
ART_W, ART_H = 2624, 1472


def font(size, bold=True):
    cands = ([r"C:\Windows\Fonts\msyhbd.ttc"] if bold else []) + \
            [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    a = sys.argv[1:]
    zid = a[0]
    vals = [float(v) for v in a[1:5]]
    if max(vals) <= 1.0 and all(v <= 1.0 for v in vals):
        x0, y0, x1, y1 = [int(v * (ART_W if i % 2 == 0 else ART_H)) for i, v in enumerate(vals)]
        # 归一化时第二对是右/下边界
        x1 = int(vals[2] * ART_W)
        y1 = int(vals[3] * ART_H)
    else:
        x0, y0, x1, y1 = [int(v) for v in vals]
    outw = int(a[5]) if len(a) > 5 else 1400

    doc = json.loads(open(LEVELS, encoding="utf-8").read())
    zmap = {z["id"]: z for z in doc["map"]["zones"]}
    z = zmap[zid]
    art = os.path.join(REPO, z["art"].replace("/", os.sep))
    im = Image.open(art).convert("RGB")
    if im.size != (ART_W, ART_H):
        im = im.resize((ART_W, ART_H), Image.LANCZOS)
    im = im.crop((x0, y0, x1, y1))
    cw, ch = im.size
    sc = outw / cw
    im = im.resize((outw, int(ch * sc)), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    d = ImageDraw.Draw(im, "RGBA")

    span = max(cw, ch)
    step = 50 if span <= 420 else (100 if span <= 900 else (200 if span <= 1800 else 400))
    ft = font(max(10, int(11 / sc)))
    for gx in range(0, ART_W + 1, step):
        if gx < x0 - step or gx > x1 + step:
            continue
        px = (gx - x0) * sc
        major = (gx % (step * 5) == 0)
        d.line([px, 0, px, im.size[1]], fill=(0, 120, 255, 90 if not major else 170),
               width=1 if not major else 2)
        if major:
            d.text((px + 2, 2), str(gx), font=ft, fill=(0, 70, 200, 255))
    for gy in range(0, ART_H + 1, step):
        if gy < y0 - step or gy > y1 + step:
            continue
        py = (gy - y0) * sc
        major = (gy % (step * 5) == 0)
        d.line([0, py, im.size[0], py], fill=(0, 120, 255, 90 if not major else 170),
               width=1 if not major else 2)
        if major:
            d.text((2, py + 2), str(gy), font=ft, fill=(0, 70, 200, 255))

    fr = font(max(12, int(14 / sc)))
    for i, o in enumerate(z["objects"]):
        px, py = (o["x"] - x0) * sc, (o["y"] - y0) * sc
        r = o["r"] * sc
        d.ellipse([px - r, py - r, px + r, py + r], outline=(220, 20, 20, 220), width=2)
        d.line([px - 8, py, px + 8, py], fill=(0, 200, 255, 255), width=2)
        d.line([px, py - 8, px, py + 8], fill=(0, 200, 255, 255), width=2)
        lbl = "%d%s" % (i + 1, o["char"])
        d.text((px + r + 2, py - 8), lbl, font=fr, fill=(220, 30, 30, 255),
               stroke_width=2, stroke_fill=(255, 255, 255, 255))

    head = "%s %s  crop=(%d,%d)-(%d,%d)  grid=%dpx  scale=%.3f" % (
        zid, z["name"], x0, y0, x1, y1, step, sc)
    d.rectangle([0, 0, im.size[0], 20], fill=(0, 0, 0, 150))
    d.text((4, 3), head, font=font(12), fill=(255, 255, 255, 255))
    p = os.path.join(OUT, "%s_%d_%d_%d_%d.png" % (zid, x0, y0, x1, y1))
    im.save(p)
    print(p, im.size)


if __name__ == "__main__":
    main()
