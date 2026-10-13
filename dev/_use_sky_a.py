# -*- coding: utf-8 -*-
"""把 01 天象换成"第一张"（方案 A），并做与前面一致的核查。

方案 A 与 B 的差别（用户选 A）：
  A：日在中偏左、**大幅**（带暖光晕，透过云层）、月牙在**左上角**，
     云带横过右上，右侧雷雨云带闪电；中段天空留空。
  B：日偏小在左上、月牙在右上，斜云带贯穿全幅。（已弃用）

底部渐隐照旧保留：需求写明底部要叠地图名称与暗色渐变，
核查底部带细节量若超阈值就压一压，这一步对 A/B 一视同仁。
"""
import os

import numpy as np
from PIL import Image

SRC = r"C:\Users\32058\.dsh\profiles\desktop\task_jNetnsnweSnXaQP7aU8SYh1O7Xdfv6Ua.png"
OUT = r"C:\DSH\字趣\out\minimaps\minimap-01-天象.jpg"
TW, TH = 2624, 1472

FADE_FROM = 0.86
MAX_ALPHA = 150 / 255.0
INK = np.array([38, 30, 22], dtype=np.float32)


def detail(img, box):
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("L").crop((x0, y0, x1, y1)), dtype=np.float32)
    return float(a.std())


im = Image.open(SRC).convert("RGB")
if abs(im.size[0] / float(im.size[1]) - TW / float(TH)) > 0.01:
    raise SystemExit("!! 宽高比不是 16:9：%s" % (im.size,))
if im.size != (TW, TH):
    im = im.resize((TW, TH), Image.LANCZOS)

tl = detail(im, (0, 0, int(TW * 0.18), int(TH * 0.14)))
bt_before = detail(im, (0, int(TH * 0.84), TW, TH))
ce = detail(im, (int(TW * 0.30), int(TH * 0.28), int(TW * 0.70), int(TH * 0.72)))

# 底部暖墨渐隐（只在下方 14% 内，平滑收到 59%，不是全黑）
a = np.asarray(im, dtype=np.float32)
y0 = int(TH * FADE_FROM)
t = np.clip((np.arange(TH) - y0) / float(TH - y0), 0.0, 1.0)
ramp = np.zeros((TH, 1, 1), dtype=np.float32)
ramp[:, 0, 0] = (t ** 1.6) * MAX_ALPHA
a = a * (1.0 - ramp) + INK[None, None, :] * ramp
im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
im.save(OUT, "JPEG", quality=93, optimize=True)

bt_after = detail(Image.open(OUT), (0, int(TH * 0.84), TW, TH))
print("  01 天象（方案 A）  %dx%d" % im.size)
print("    左上角(叠编号) %.1f   中心 %.1f" % (tl, ce))
print("    底部带(叠名称) %.1f -> %.1f  %s"
      % (bt_before, bt_after, "在阈值内" if bt_after <= 42 else "仍偏高"))
print("    %s  %d KB" % (OUT, os.path.getsize(OUT) // 1024))
