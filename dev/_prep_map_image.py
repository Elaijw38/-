# -*- coding: utf-8 -*-
"""处理用户重新生成的水墨地图（webp）→ 部署用的 JPEG + 读图定位预览。

做三件事：
  1) 裁掉右下角「豆包 AI 生成」水印
  2) 缩到 1800 宽并压缩（原 2048×1152，偏大）
  3) 输出一张带 100px 刻度的预览，用来按图上实际地物重标热区
"""
import io, os, subprocess
from PIL import Image, ImageDraw

SRC = (r"C:\Users\32058\.dsh\attachments\v1\objects\b5"
       r"\b575ebe309f45ee48e078751364fea8a4eda482bb83423f9293d3c2bd757b49f")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

im = Image.open(SRC).convert("RGB")
W, H = im.size
print("原图: %dx%d  %.2f MB  格式=%s" % (W, H, os.path.getsize(SRC) / 1048576,
                                      Image.open(SRC).format))

# 1) 水印在右下角，从底部去掉 120px
CROP_BOTTOM = 120
im2 = im.crop((0, 0, W, H - CROP_BOTTOM))
print("裁掉底部 %dpx（去水印）→ %dx%d" % (CROP_BOTTOM, im2.width, im2.height))

# 2) 缩到 1800 宽
TARGET_W = 1800
scale = TARGET_W / im2.width
im3 = im2.resize((TARGET_W, int(round(im2.height * scale))), Image.LANCZOS)
out = os.path.join(ASSETS, "wangyi-map.jpg")
im3.save(out, "JPEG", quality=86, optimize=True, progressive=True)
print("写出: %s  %.2f MB  尺寸 %dx%d" % (out, os.path.getsize(out) / 1048576,
                                        im3.width, im3.height))
print("viewBox 应为: 0 0 %d %d" % (im3.width, im3.height))

# 3) 带刻度预览（每 100px 一格），用来读图定位
prev = im3.copy()
d = ImageDraw.Draw(prev, "RGBA")
for x in range(0, prev.width, 100):
    d.line([(x, 0), (x, prev.height)], fill=(210, 30, 10, 95), width=1)
    d.text((x + 3, 4), str(x), fill=(210, 30, 10, 235))
for y in range(0, prev.height, 100):
    d.line([(0, y), (prev.width, y)], fill=(210, 30, 10, 95), width=1)
    d.text((4, y + 3), str(y), fill=(210, 30, 10, 235))
grid = os.path.join(os.environ["TEMP"], "map_grid2.png")
prev.save(grid)
print("刻度预览: %s" % grid)
