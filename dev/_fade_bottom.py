# -*- coding: utf-8 -*-
"""给 01 天象底部加一道暗色渐隐，让网页叠的地图名称读得清楚。

为什么只做这一处改动：
  核查量到底部带细节量 50.9（阈值 42）——底部芦苇与水面反光太密，
  地图名称压上去会跟画面抢。而这正是需求里写明"底部会叠加名称和暗色渐变"
  要避免的情况，所以这是**修一个已知冲突**，不是重画。
  因此画面内容、构图、色调一律不动，只在最下面加一层渐隐。

渐隐参数刻意保守：
  · 只覆盖下方 14%，从透明平滑收到最深处 alpha 150（约 59%），
    不到全黑——保留地貌可读，画面不会变成"半张图"。
  · 用暖墨色而不是纯黑，跟绢帛底子同源，不会显出一块贴片。
"""
import os

import numpy as np
from PIL import Image

P = r"C:\DSH\字趣\out\minimaps\minimap-01-天象.jpg"
W, H = 2624, 1472

FADE_FROM = 0.86          # 从 86% 高度开始渐隐
MAX_ALPHA = 150 / 255.0   # 最深处的不透明度（约 59%）
INK = np.array([38, 30, 22], dtype=np.float32)   # 暖墨色，与绢帛同源


def detail(img, box):
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("L").crop((x0, y0, x1, y1)), dtype=np.float32)
    return float(a.std())


before = detail(Image.open(P), (0, int(H * 0.84), W, H))

im = Image.open(P).convert("RGB")
a = np.asarray(im, dtype=np.float32)

y0 = int(H * FADE_FROM)
ramp = np.zeros((H, 1, 1), dtype=np.float32)
t = np.clip((np.arange(H) - y0) / float(H - y0), 0.0, 1.0)   # 0 → 1
# 平滑一点：用平方，避免顶部出现可见的起始线
ramp[:, 0, 0] = (t ** 1.6) * MAX_ALPHA

out = a * (1.0 - ramp) + INK[None, None, :] * ramp
out = np.clip(out, 0, 255).astype(np.uint8)
Image.fromarray(out, "RGB").save(P, "JPEG", quality=93, optimize=True)

after = detail(Image.open(P), (0, int(H * 0.84), W, H))
print("  底部带细节量  %.1f -> %.1f   %s"
      % (before, after, "已降到阈值内" if after <= 42 else "仍偏高"))
print("  %s  %d KB" % (P, os.path.getsize(P) // 1024))
