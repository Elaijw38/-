# -*- coding: utf-8 -*-
"""换上新的殷商王邑底图（不裁切版）。

为什么改主意不裁成 2:1：2:1 要砍掉底部 150px，河上那条「舟」就贴到画面下边缘
（y≈890/907），热区会被裁掉一半。改用完整 16:9 后：
  缩放系数与原方案完全相同（0.6861），所以【已读出的 y 坐标全部沿用】，
  只是画布从 907 变高到 1010，底部河滩回来了，舟有了余量。

viewBox 随之改为 0 0 1800 1010。
"""
import os, shutil
from PIL import Image, ImageDraw

SRC = r"C:\Users\32058\.dsh\profiles\desktop\task_VOFWu2oZYMmINTHgZ6WMf8B4KKZHuJyj.png"
REPO = r"C:\DSH\字趣"
OUT = os.path.join(REPO, "assets", "wangyi-map.jpg")
BAK = os.path.join(REPO, "assets", "wangyi-map.豆包旧图.bak.jpg")
PREV = os.path.join(REPO, "_check")

VW = 1800
VH = round(VW * 1472 / 2624)          # 1010
print("目标画布: %dx%d（16:9，不裁切）" % (VW, VH))

im = Image.open(SRC).convert("RGB")
im2 = im.resize((VW, VH), Image.LANCZOS)
os.makedirs(PREV, exist_ok=True)
if os.path.exists(OUT) and not os.path.exists(BAK):
    shutil.copy2(OUT, BAK)
    print("旧底图已备份")
im2.save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
print("已写出 %s  %.2f MB" % (OUT, os.path.getsize(OUT) / 1048576))

# 整体网格
g = im2.copy(); d = ImageDraw.Draw(g)
for x in range(0, VW + 1, 100): d.line([(x, 0), (x, VH)], fill=(255, 0, 0), width=1)
for y in range(0, VH + 1, 100): d.line([(0, y), (VW, y)], fill=(255, 0, 0), width=1)
for x in range(0, VW + 1, 200):
    for y in range(0, VH + 1, 100):
        d.text((x + 3, y + 2), "%d,%d" % (x, y), fill=(255, 0, 0))
g.save(os.path.join(PREV, "map_grid_full.png"))

# 分块：3 列 × 3 行，覆盖全高（含新回来的底部）
COLS, ROWS = 3, 3
tw, thh = VW // COLS, VH // ROWS
for r in range(ROWS):
    for c in range(COLS):
        x0, y0 = c * tw, r * thh
        x1 = VW if c == COLS - 1 else x0 + tw
        y1 = VH if r == ROWS - 1 else y0 + thh
        tile = im2.crop((x0, y0, x1, y1))
        k = max(1, 1400 // tile.width)
        tile = tile.resize((tile.width * k, tile.height * k), Image.LANCZOS)
        td = ImageDraw.Draw(tile)
        for x in range(x0, x1 + 1, 50):
            px = (x - x0) * k; major = (x % 100 == 0)
            td.line([(px, 0), (px, tile.height)], fill=(255, 0, 0) if major else (255, 160, 160), width=2 if major else 1)
            if major:
                td.text((px + 3, 3), str(x), fill=(255, 0, 0)); td.text((px + 3, tile.height - 14), str(x), fill=(255, 0, 0))
        for y in range(y0, y1 + 1, 50):
            py = (y - y0) * k; major = (y % 100 == 0)
            td.line([(0, py), (tile.width, py)], fill=(255, 0, 0) if major else (255, 160, 160), width=2 if major else 1)
            if major:
                td.text((3, py + 3), str(y), fill=(255, 0, 0)); td.text((tile.width - 34, py + 3), str(y), fill=(255, 0, 0))
        tile.save(os.path.join(PREV, "t_r%dc%d.png" % (r + 1, c + 1)))
        print("  分块 t_r%dc%d  x[%d,%d] y[%d,%d]" % (r + 1, c + 1, x0, x1, y0, y1))
