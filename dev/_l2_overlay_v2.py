# -*- coding: utf-8 -*-
"""第二关热点校准预览（v2）：把 levels.json 里的热点画到分区插画上。

用途：肉眼核对「每个热点是否真的落在图上可辨认的物件中心」。
不修改任何数据，只出图。

用法：
  python dev/_l2_overlay_v2.py                 # 全部五区 + 大地图
  python dev/_l2_overlay_v2.py beast life      # 只出指定区
  python dev/_l2_overlay_v2.py --crop life 0.25 0.55 0.75 1.0   # 局部放大（归一化坐标）
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(REPO, "js", "core", "levels.json")
OUT = os.path.join(REPO, "out", "l2-calib-v2")

ART_W, ART_H = 2624, 1472
DISPLAY_W = 1600          # 输出图宽度


def font(size):
    for p in (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
              r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_zone(zone, mp, tag="", crop=None):
    art = os.path.join(REPO, zone["art"].replace("/", os.sep))
    im = Image.open(art).convert("RGB")
    if im.size != (ART_W, ART_H):
        im = im.resize((ART_W, ART_H), Image.LANCZOS)

    objs = zone["objects"]
    sx = sy = 1.0
    ox = oy = 0
    if crop:
        x0, y0, x1, y1 = crop
        box = (int(x0 * ART_W), int(y0 * ART_H), int(x1 * ART_W), int(y1 * ART_H))
        im = im.crop(box)
        ox, oy = box[0], box[1]

    disp_h = int(im.size[1] * DISPLAY_W / im.size[0])
    im = im.resize((DISPLAY_W, disp_h), Image.LANCZOS)
    s = DISPLAY_W / (ART_W * (crop[2] - crop[0]) if crop else ART_W)
    d = ImageDraw.Draw(im, "RGBA")

    fr = font(max(14, int(20 * s * 1.6)))
    fs = font(max(11, int(14 * s * 1.6)))

    for i, o in enumerate(objs):
        x = (o["x"] - ox) * s
        y = (o["y"] - oy) * s
        r = o["r"] * s
        d.ellipse([x - r, y - r, x + r, y + r], outline=(220, 30, 30, 230), width=3)
        d.line([x - 9, y, x + 9, y], fill=(0, 90, 220, 255), width=3)
        d.line([x, y - 9, x, y + 9], fill=(0, 90, 220, 255), width=3)
        lbl = "%d %s" % (i + 1, o["char"])
        tw = d.textlength(lbl, font=fr)
        bx, by = x - tw / 2 - 5, y - r - 26
        if by < 0:
            by = y + r + 4
        d.rectangle([bx, by, bx + tw + 10, by + 24], fill=(255, 255, 255, 225),
                    outline=(220, 30, 30, 255), width=2)
        d.text((bx + 5, by + 3), lbl, font=fr, fill=(150, 20, 20, 255))

    head = "%s  %s  %d 个热点" % (zone["id"], zone["name"], len(objs))
    if tag:
        head += "  [" + tag + "]"
    d.rectangle([0, 0, DISPLAY_W, 30], fill=(20, 20, 20, 210))
    d.text((8, 5), head + "   " + zone["art"], font=fs, fill=(255, 255, 255, 255))

    os.makedirs(OUT, exist_ok=True)
    name = "%s%s%s.png" % (zone["id"], ("_" + tag) if tag else "",
                           ("_crop" if crop else ""))
    p = os.path.join(OUT, name)
    im.save(p)
    print("  %s  (%dx%d, %d 热点)" % (os.path.relpath(p, REPO), im.size[0], im.size[1], len(objs)))
    return p


def draw_world(mp, tag=""):
    art = os.path.join(REPO, (mp.get("worldImage") or mp.get("bgImage")).replace("/", os.sep))
    im = Image.open(art).convert("RGB")
    if im.size != (ART_W, ART_H):
        im = im.resize((ART_W, ART_H), Image.LANCZOS)
    disp_h = int(ART_H * DISPLAY_W / ART_W)
    im = im.resize((DISPLAY_W, disp_h), Image.LANCZOS)
    s = DISPLAY_W / ART_W
    d = ImageDraw.Draw(im, "RGBA")
    fr = font(22)
    fs = font(15)
    for i, z in enumerate(mp["zones"]):
        w = z["world"]
        x, y, r = w["x"] * s, w["y"] * s, w["r"] * s
        d.ellipse([x - r, y - r, x + r, y + r], outline=(0, 130, 60, 235), width=4)
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(0, 130, 60, 255))
        lbl = "%d %s" % (i + 1, z["name"])
        tw = d.textlength(lbl, font=fr)
        d.rectangle([x - tw / 2 - 6, y - 34, x + tw / 2 + 6, y - 4],
                    fill=(255, 255, 255, 230), outline=(0, 130, 60, 255), width=2)
        d.text((x - tw / 2, y - 32), lbl, font=fr, fill=(0, 90, 40, 255))
    d.rectangle([0, 0, DISPLAY_W, 30], fill=(20, 20, 20, 210))
    d.text((8, 5), "WORLD 大地图入口 " + str(len(mp["zones"])), font=fs, fill=(255, 255, 255, 255))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "world%s.png" % (("_" + tag) if tag else ""))
    im.save(p)
    print("  %s" % os.path.relpath(p, REPO))
    return p


def main():
    args = sys.argv[1:]
    doc = json.loads(io.open(LEVELS, encoding="utf-8").read())
    mp = doc["map"]
    crop = None
    if "--crop" in args:
        k = args.index("--crop")
        zid = args[k + 1]
        crop = tuple(float(v) for v in args[k + 2:k + 6])
        args = args[:k]
    zmap = {z["id"]: z for z in mp["zones"]}
    if crop:
        draw_zone(zmap[zid], mp, tag="crop", crop=crop)
        return 0
    want = [a for a in args if a in zmap]
    if not want:
        want = list(zmap.keys())
        draw_world(mp)
    for zid in want:
        draw_zone(zmap[zid], mp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
