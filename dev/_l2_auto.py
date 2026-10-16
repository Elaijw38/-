# -*- coding: utf-8 -*-
"""第二关：目标物**连通块质心**测量（不依赖 scipy）。

以现有热点为中心取窗口 → 与纸色差异过阈值的像素为"物件"→ 连通块标记 →
取「在热点半径内占比最高」的那一块 → 输出它的质心与包围盒。

这样能把动物/器物与旁边的石头、草丛分开，读数可直接用于改坐标。

用法：
  python dev/_l2_auto.py beast
  python dev/_l2_auto.py life 鼎 缶 酉
  python dev/_l2_auto.py beast --win 3.0 --thr 30
"""
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(REPO, "js", "core", "levels.json")
ART_W, ART_H = 2624, 1472


def components(mask, min_area):
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    cur = 0
    out = []
    for sy in range(h):
        row = mask[sy]
        for sx in range(w):
            if row[sx] and lab[sy, sx] == 0:
                cur += 1
                q = deque([(sy, sx)])
                lab[sy, sx] = cur
                px = []
                while q:
                    y, x = q.popleft()
                    px.append((y, x))
                    if y > 0 and mask[y - 1, x] and lab[y - 1, x] == 0:
                        lab[y - 1, x] = cur; q.append((y - 1, x))
                    if y < h - 1 and mask[y + 1, x] and lab[y + 1, x] == 0:
                        lab[y + 1, x] = cur; q.append((y + 1, x))
                    if x > 0 and mask[y, x - 1] and lab[y, x - 1] == 0:
                        lab[y, x - 1] = cur; q.append((y, x - 1))
                    if x < w - 1 and mask[y, x + 1] and lab[y, x + 1] == 0:
                        lab[y, x + 1] = cur; q.append((y, x + 1))
                if len(px) >= min_area:
                    a = np.array(px)
                    out.append({"area": len(px),
                                "cy": float(a[:, 0].mean()), "cx": float(a[:, 1].mean()),
                                "y0": int(a[:, 0].min()), "y1": int(a[:, 0].max()),
                                "x0": int(a[:, 1].min()), "x1": int(a[:, 1].max())})
    return out


def main():
    a = sys.argv[1:]
    zid = a[0]
    rest = a[1:]
    winf, thr = 2.6, 34.0
    if "--win" in rest:
        k = rest.index("--win"); winf = float(rest[k + 1]); rest = rest[:k] + rest[k + 2:]
    if "--thr" in rest:
        k = rest.index("--thr"); thr = float(rest[k + 1]); rest = rest[:k] + rest[k + 2:]
    only = [c for c in rest if not c.startswith("--")]

    doc = json.loads(open(LEVELS, encoding="utf-8").read())
    z = {x["id"]: x for x in doc["map"]["zones"]}[zid]
    im = Image.open(os.path.join(REPO, z["art"].replace("/", os.sep))).convert("RGB")
    if im.size != (ART_W, ART_H):
        im = im.resize((ART_W, ART_H), Image.LANCZOS)
    arr = np.asarray(im).astype(np.float32)

    print("zone=%s  窗口=x%.1f r  阈值=%.0f" % (zid, winf, thr))
    print("%-4s %-14s %-16s %-9s %s" % ("字", "现有(x,y,r)", "连通块质心", "位移", "块包围盒 尺寸 面积/占比"))
    for o in z["objects"]:
        if only and o["char"] not in only:
            continue
        win = max(160, int(o["r"] * winf))
        x0, x1 = max(0, o["x"] - win), min(ART_W, o["x"] + win)
        y0, y1 = max(0, o["y"] - win), min(ART_H, o["y"] + win)
        sub = arr[y0:y1, x0:x1]
        ring = np.concatenate([sub[0:4].reshape(-1, 3), sub[-4:].reshape(-1, 3),
                               sub[:, 0:4].reshape(-1, 3), sub[:, -4:].reshape(-1, 3)])
        bg = np.median(ring, axis=0)
        # 物件 = 「有彩度」或「明显比纸暗」。地面柔影只压暗一点点、几乎无彩度，会被排除。
        sat = sub.max(axis=2) - sub.min(axis=2)
        bg_lum = float(bg.mean())
        lum = sub.mean(axis=2)
        mask = (sat > 30) | (lum < bg_lum - thr)

        comps = components(mask, min_area=max(300, int((o["r"] * 0.35) ** 2)))
        if not comps:
            print("%-4s (%4d,%4d,%3d)  ← 窗口内没有成规模的块 (win=%d)" % (o["char"], o["x"], o["y"], o["r"], win))
            continue
        lx, ly = o["x"] - x0, o["y"] - y0
        rr = float(o["r"])
        scored = []
        for c in comps:
            dx = max(c["x0"] - lx, 0, lx - c["x1"])
            dy = max(c["y0"] - ly, 0, ly - c["y1"])
            d = (dx * dx + dy * dy) ** 0.5
            inside = 1.0 if (c["x0"] <= lx <= c["x1"] and c["y0"] <= ly <= c["y1"]) else 0.0
            scored.append((inside, -d, c["area"], c))
        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
        c = scored[0][3]
        cx, cy = c["cx"] + x0, c["cy"] + y0
        print("%-4s (%4d,%4d,%3d)  (%4d,%4d)   %+5.0f,%+5.0f   [%4d,%4d]-[%4d,%4d] %4dx%-4d area=%d"
              % (o["char"], o["x"], o["y"], o["r"], cx, cy, cx - o["x"], cy - o["y"],
                 c["x0"] + x0, c["y0"] + y0, c["x1"] + x0, c["y1"] + y0,
                 c["x1"] - c["x0"], c["y1"] - c["y0"], c["area"]))


if __name__ == "__main__":
    main()
