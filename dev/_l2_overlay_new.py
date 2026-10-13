# -*- coding: utf-8 -*-
"""第二关：在**最新六张图**上叠加热点，出校准校验图。

为什么要重做一遍：`out/level2-maps/*.jpg` 里的大地图与人居器物图
在位图之后就改过构图（world/life 的修改时间 22:53 晚于 hotspots.json 的 22:47），
旧图上的标记不能再用。本脚本一律以 `out/level2-maps/` 的**当前**图为准。

坐标空间：2624 × 1472（分区插画自己的像素空间）。
即 `dev/_apply_level2.py` 里 XY 那一份，也是 `out/level2-maps/hotspots.json`
的那一份。**不是** `levels.json` 里遗留的 1800×1010 旧王邑坐标。

用法：
  python dev/_l2_overlay_new.py                 # 全部五区 + 大地图
  python dev/_l2_overlay_new.py life            # 只出某区
  python dev/_l2_overlay_new.py --crop life 900 600 700 500   # 再出一张局部放大图
"""
import io
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "out", "level2-maps")
OUT = os.path.join(REPO, "out", "level2-maps", "_calib")
W, H = 2624, 1472

ZONES = [
    ("sky",   "level2-01-sky-天象.jpg",       "01-sky"),
    ("land",  "level2-02-land-山川.jpg",      "02-land"),
    ("plant", "level2-03-plant-草木.jpg",     "03-plant"),
    ("beast", "level2-04-beast-禽兽虫鱼.jpg", "04-beast"),
    ("life",  "level2-05-life-人居器物.jpg",  "05-life"),
]
WORLD = "level2-00-world-大地图.jpg"


def load_xy():
    """从 js/core/levels.json 读坐标——那才是**写入运行时数据的真源**。

    真源的上一层是 dev/_l2_calibrate.py 的 TABLE；
    levels.json 已由它写入并附 form 字段，这里直接读 JSON 最稳。
    返回 {zoneId: {char: (x, y, r, form)}}。
    """
    doc = json.loads(io.open(os.path.join(REPO, "js", "core", "levels.json"),
                             encoding="utf-8").read())
    out = {}
    for z in doc["map"]["zones"]:
        out[z["id"]] = {o["char"]: (o["x"], o["y"], o["r"], o.get("form", ""))
                        for o in z["objects"]}
    return out


def font(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_overlay(imgfile, marks, outpng, title, crop=None):
    """marks: [(char, x, y, r, note)]"""
    im = Image.open(os.path.join(SRC, imgfile)).convert("RGB")
    if im.size != (W, H):
        raise SystemExit("!! %s 尺寸是 %s，不是 %d×%d" % (imgfile, im.size, W, H))
    scale = 1.0
    if crop:
        cx, cy, cw, ch = crop
        im = im.crop((cx, cy, cx + cw, cy + ch))
        scale = 1.7 if cw < 1200 else 1.0
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im, "RGBA")
    f = font(30 if scale >= 1.5 else 26)
    fs = font(24 if scale >= 1.5 else 20)
    for ch, x, y, r, note in marks:
        px, py = x * scale, y * scale
        if crop:
            px, py = (x - crop[0]) * scale, (y - crop[1]) * scale
            if not (-80 <= px <= im.width + 80 and -80 <= py <= im.height + 80):
                continue
        rr = max(4, r * scale)
        d.ellipse([px - rr, py - rr, px + rr, py + rr], outline=(255, 40, 20, 255), width=3)
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(255, 255, 0, 255))
        d.line([px - rr - 10, py, px - rr, py], fill=(255, 40, 20, 255), width=3)
        d.line([px + rr, py, px + rr + 10, py], fill=(255, 40, 20, 255), width=3)
        label = ch
        bb = d.textbbox((0, 0), label, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        lx, ly = px + rr + 10, py - th - 6
        if lx + tw + 8 > im.width:
            lx = px - rr - 12 - tw
        d.rectangle([lx - 4, ly - 4, lx + tw + 6, ly + th + 8], fill=(20, 16, 12, 210))
        d.text((lx, ly), label, font=f, fill=(255, 226, 150, 255))
        if note and scale >= 1.5:
            d.text((lx, ly + th + 8), note, font=fs, fill=(210, 200, 180, 230))
    d.rectangle([0, 0, im.width - 1, 46], fill=(20, 16, 12, 200))
    d.text((14, 8), title, font=font(28), fill=(255, 226, 150, 255))
    im.save(outpng)
    return outpng


def main():
    xy = load_xy()
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    crop = None
    only = None
    if args and args[0] == "--crop":
        only = args[1]
        crop = tuple(int(v) for v in args[2:6])
    elif args:
        only = args[0]

    made = []
    for zid, imgfile, key in ZONES:
        if only and only not in ("world",) and only != zid:
            continue
        if only == "world" and zid != "world":
            pass
        if not only and False:
            pass
        marks = []
        for ch, (x, y, r, form) in xy[zid].items():
            marks.append((ch, x, y, r, ""))
        if crop:
            png = os.path.join(OUT, "%s-zoom.png" % key)
            made.append(draw_overlay(imgfile, marks, png,
                                     "%s · 局部 %s" % (zid, crop), crop))
        else:
            png = os.path.join(OUT, "%s-calib.png" % key)
            made.append(draw_overlay(imgfile, marks, png, "%s · %d 个热点" % (zid, len(marks))))

    if not only or only == "world":
        # 大地图：只标五区入口，验证点位是否落在对应主题区域
        doc = json.loads(io.open(os.path.join(REPO, "js", "core", "levels.json"),
                                 encoding="utf-8").read())
        pins = doc["map"].get("worldPins") or {}
        NAMES = {"sky": "天象", "land": "山川", "plant": "草木",
                 "beast": "禽兽虫鱼", "life": "人居器物"}
        marks = []
        for zid, zname in NAMES.items():
            p = pins.get(zid)
            if p:
                marks.append((zname, p["x"], p["y"], 90, zid))
        made.append(draw_overlay(WORLD, marks,
                                 os.path.join(OUT, "00-world-calib.png"), "world · 五区入口"))
    for p in made:
        print("  %s  (%d B)" % (os.path.relpath(p, REPO), os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
