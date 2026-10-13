# -*- coding: utf-8 -*-
"""带像素网格与刻度的校验图：用来**读出**准确坐标，而不是靠目测估。

图很大（2624×1472），先把「原图 + 每 100px 细线 / 每 200px 粗线 + 边缘刻度」
落成一张参考图，再按九宫切块放大——每块只 875×491 像素，
在 1.5 倍放大下能直接看出目标物落在哪两格线之间。

用法：
  python dev/_l2_grid.py world              # 大地图：整张 + 3×3 分块
  python dev/_l2_grid.py life               # 某区：整张 + 3×3 分块
  python dev/_l2_grid.py life --tile 1 0    # 只出第 (列,行) 块
  python dev/_l2_grid.py life --marks       # 分块上再叠现有热点，看偏差
"""
import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "out", "level2-maps")
OUT = os.path.join(REPO, "out", "level2-maps", "_grid")
W, H = 2624, 1472

ZONES = {
    "sky":   "level2-01-sky-天象.jpg",
    "land":  "level2-02-land-山川.jpg",
    "plant": "level2-03-plant-草木.jpg",
    "beast": "level2-04-beast-禽兽虫鱼.jpg",
    "life":  "level2-05-life-人居器物.jpg",
    "world": "level2-00-world-大地图.jpg",
}


def font(size, bold=False):
    cands = ([r"C:\Windows\Fonts\msyhbd.ttc"] if bold else []) + [
        r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def add_grid(im, step=100):
    d = ImageDraw.Draw(im, "RGBA")
    f = font(18)
    for x in range(0, W + 1, step):
        big = (x % (step * 2) == 0)
        d.line([x, 0, x, H], fill=(255, 60, 40, 110 if big else 55), width=2 if big else 1)
    for y in range(0, H + 1, step):
        big = (y % (step * 2) == 0)
        d.line([0, y, W, y], fill=(255, 60, 40, 110 if big else 55), width=2 if big else 1)
    # 刻度：只写 200 的倍数，避免糊
    for x in range(0, W + 1, 200):
        for yy in (6, H - 30):
            d.rectangle([x + 2, yy, x + 62, yy + 24], fill=(15, 12, 9, 190))
            d.text((x + 5, yy + 2), str(x), font=f, fill=(255, 226, 150, 255))
    for y in range(0, H + 1, 200):
        for xx in (6, W - 76):
            d.rectangle([xx, y + 2, xx + 70, y + 26], fill=(15, 12, 9, 190))
            d.text((xx + 5, y + 4), str(y), font=f, fill=(255, 226, 150, 255))
    return im


def load_marks(zid):
    """从 _apply_level2.py 读现有 XY（用于叠图看偏差）。"""
    import json
    import re
    src = io.open(os.path.join(REPO, "dev", "_apply_level2.py"), encoding="utf-8").read()
    m = re.search(r"^XY = \{", src, re.M)
    out, cur = {}, None
    for raw in src[m.end():].splitlines():
        line = re.sub(r"#.*", "", raw)
        if not line.strip():
            continue
        zm = re.match(r'\s*"([a-z]+)"\s*:\s*\{', line)
        if zm:
            cur = zm.group(1)
            out[cur] = {}
            continue
        if re.match(r"\s*\},?\s*$", line) and cur:
            cur = None
            continue
        if cur:
            for cm in re.finditer(r'"([^"]+)"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', line):
                out[cur][cm.group(1)] = [int(cm.group(2)), int(cm.group(3)), int(cm.group(4))]
    return out.get(zid, {})


def draw_marks(im, marks, off=(0, 0), scale=1.0):
    d = ImageDraw.Draw(im, "RGBA")
    f = font(26)
    for ch, (x, y, r) in marks.items():
        px, py = (x - off[0]) * scale, (y - off[1]) * scale
        if not (-60 <= px <= im.width + 60 and -60 <= py <= im.height + 60):
            continue
        rr = max(6, r * scale)
        d.ellipse([px - rr, py - rr, px + rr, py + rr], outline=(0, 255, 120, 230), width=3)
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(255, 255, 0, 255))
        d.text((px + rr + 6, py - rr - 4), ch, font=f, fill=(120, 255, 170, 255))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    zid = args[0]
    if zid not in ZONES:
        print("!! 未知区：%s（可选 %s）" % (zid, "/".join(ZONES)))
        return 1
    want_marks = "--marks" in args
    tile = None
    if "--tile" in args:
        i = args.index("--tile")
        tile = (int(args[i + 1]), int(args[i + 2]))
    os.makedirs(OUT, exist_ok=True)
    base = Image.open(os.path.join(SRC, ZONES[zid])).convert("RGB")
    if base.size != (W, H):
        raise SystemExit("!! 尺寸异常 %s" % (base.size,))

    marks = load_marks(zid) if want_marks else {}
    tag = "-marks" if want_marks else ""

    # 整张（缩到 1312 宽，够看构图与五区入口）
    full = add_grid(base.copy())
    if marks:
        draw_marks(full, marks)
    p = os.path.join(OUT, "%s-grid-full%s.png" % (zid, tag))
    full.resize((1312, 736), Image.LANCZOS).save(p)
    print("  %s" % os.path.relpath(p, REPO))

    # 3×3 分块（每块 875×491 → 放大 1.6 倍）
    tw, th = W // 3 + 1, H // 3 + 1
    tiles = [(c, r) for r in range(3) for c in range(3)]
    if tile:
        tiles = [tile]
    for c, r in tiles:
        box = (c * (W // 3), r * (H // 3),
               min(W, c * (W // 3) + tw), min(H, r * (H // 3) + th))
        sub = base.crop(box)
        sub = sub.resize((int(sub.width * 1.6), int(sub.height * 1.6)), Image.LANCZOS)
        sd = ImageDraw.Draw(sub, "RGBA")
        f = font(22)
        for x in range(0, W + 1, 100):
            px = (x - box[0]) * 1.6
            if 0 <= px <= sub.width:
                sd.line([px, 0, px, sub.height], fill=(255, 60, 40, 90), width=1)
                sd.text((px + 3, 4), str(x), font=f, fill=(255, 226, 150, 255))
        for y in range(0, H + 1, 100):
            py = (y - box[1]) * 1.6
            if 0 <= py <= sub.height:
                sd.line([0, py, sub.width, py], fill=(255, 60, 40, 90), width=1)
                sd.text((4, py + 3), str(y), font=f, fill=(255, 226, 150, 255))
        if marks:
            draw_marks(sub, marks, off=(box[0], box[1]), scale=1.6)
        p = os.path.join(OUT, "%s-tile%d%d%s.png" % (zid, c, r, tag))
        sub.save(p)
        print("  %s  box=%s" % (os.path.relpath(p, REPO), box))
    return 0


if __name__ == "__main__":
    sys.exit(main())
