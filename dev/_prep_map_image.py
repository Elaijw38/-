# -*- coding: utf-8 -*-
"""把豆包生成的水墨地图接入项目。

处理三件事：
  1) 裁掉右下角「豆包 AI 生成」水印（位于 y≈1071~1131）
  2) 缩到适合网页的尺寸并压缩（原 2048×1152 / 0.75MB，偏大）
  3) 存成 assets/wangyi-map.jpg，供地图作背景

同时输出裁切后的预览，便于我按图上实际地物放置甲骨文实物点。
"""
import io, os
from PIL import Image

SRC = r"C:\Users\32058\.dsh\attachments\v1\objects\73\73a964e0736a592bfb4928f6ec440f136d7efd2660d4f86543d8e61b8f81a29b"
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

im = Image.open(SRC).convert("RGB")
W, H = im.size
print("原图: %dx%d  %.2f MB" % (W, H, os.path.getsize(SRC) / 1048576))

# 1) 裁掉水印：水印文字在 y≈1071~1131，故从底部去掉 120px 留足余量
CROP_BOTTOM = 120
im2 = im.crop((0, 0, W, H - CROP_BOTTOM))
print("裁掉底部 %dpx（去水印）→ %dx%d" % (CROP_BOTTOM, im2.width, im2.height))

# 2) 缩到 1800 宽（地图在屏上约 1100px 宽，1800 足够清晰且留了余量）
TARGET_W = 1800
scale = TARGET_W / im2.width
im3 = im2.resize((TARGET_W, int(round(im2.height * scale))), Image.LANCZOS)
print("缩放 → %dx%d (比例 %.3f)" % (im3.width, im3.height, scale))

out = os.path.join(ASSETS, "wangyi-map.jpg")
im3.save(out, "JPEG", quality=86, optimize=True, progressive=True)
print("写出: %s  %.2f MB" % (out, os.path.getsize(out) / 1048576))

# 3) 另存一份「带刻度」的预览，方便我定位地物
from PIL import ImageDraw
prev = im3.copy()
d = ImageDraw.Draw(prev, "RGBA")
step = 100
for x in range(0, prev.width, step):
    d.line([(x, 0), (x, prev.height)], fill=(200, 40, 20, 90), width=1)
    d.text((x + 3, 4), str(x), fill=(200, 40, 20, 220))
for y in range(0, prev.height, step):
    d.line([(0, y), (prev.width, y)], fill=(200, 40, 20, 90), width=1)
    d.text((4, y + 3), str(y), fill=(200, 40, 20, 220))
grid = os.path.join(os.environ["TEMP"], "map_grid.png")
prev.save(grid)
print("带刻度预览: %s" % grid)
print()
print("viewBox 应设为: 0 0 %d %d" % (im3.width, im3.height))
