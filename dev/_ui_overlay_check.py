# -*- coding: utf-8 -*-
"""模拟网页 UI 叠加，直接检验"标题压上去读不读得清"。

为什么需要这个：
  "底部带"那个指标（局部标准差）只是代理量。真正要回答的是
  「按网页的做法在底部叠一道暗色渐变 + 一行标题，字读不读得清」。
  所以这里照着页面上的实际做法合成一次，再量**标题像素与其背景的对比度**。

做法：
  · 底部 26% 叠一道从透明到约 82% 的暗色渐变（与页面 .foo-bar 类做法一致）
  · 在渐变压好的位置写一行占位标题（浅色字），量字与周围背景的对比度
  · 输出叠加后的样张，可直接用眼睛复核
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = r"C:\DSH\字趣"
DST = os.path.join(REPO, "out", "minimaps")
OUT = os.path.join(REPO, "out", "_ui_check")
os.makedirs(OUT, exist_ok=True)
W, H = 2624, 1472

NAMES = ["01-天象", "02-山川", "03-草木", "04-禽兽虫鱼", "05-人居器物"]


def rel_lum(rgb):
    c = np.asarray(rgb, dtype=np.float32) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = np.maximum(la, lb), np.minimum(la, lb)
    return float((hi + 0.05) / (lo + 0.05))


FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]

print("  %-12s %-10s %-10s %s" % ("图", "底渐变后", "标题对比度", "判定"))
print("  " + "-" * 52)

for n in NAMES:
    p = os.path.join(DST, "minimap-%s.jpg" % n)
    im = Image.open(p).convert("RGB")
    a = np.asarray(im, dtype=np.float32)

    # 底部 26% 的暗色渐变（与页面叠加等效）
    y0 = int(H * 0.74)
    t = np.clip((np.arange(H) - y0) / float(H - y0), 0.0, 1.0)
    alpha = (t ** 1.3) * 0.82
    grad = alpha[:, None, None]
    dark = np.array([20, 16, 13], dtype=np.float32)
    over = a * (1.0 - grad) + dark[None, None, :] * grad

    # 量：标题文字所在带（底部约 8%）压完渐变后的背景亮度
    band = over[int(H * 0.90):int(H * 0.97), int(W * 0.06):int(W * 0.94)]
    bg_mean = band.reshape(-1, 3).mean(axis=0)
    ratio = contrast(np.array([242, 232, 213], dtype=np.float32), bg_mean)  # 浅色标题字

    # 出样张：压渐变 + 一行占位标题
    res = Image.fromarray(np.clip(over, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(res)
    font = None
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            try:
                font = ImageFont.truetype(f, 92)
                break
            except Exception:
                pass
    label = n.split("-", 1)[1]
    if font:
        d.text((int(W * 0.06), int(H * 0.905)), label, fill=(242, 232, 213), font=font)
        d.text((int(W * 0.06), int(H * 0.955)), "已点亮 0 / 61 个字形",
               fill=(214, 196, 166), font=ImageFont.truetype(font.path, 40))
    res.save(os.path.join(OUT, "ui-%s.jpg" % n), "JPEG", quality=90, optimize=True)

    verdict = "OK" if ratio >= 4.5 else ("偏弱" if ratio >= 3.0 else "不足")
    print("  %-12s %-10s %-10.2f %s" % (n, "%.0f,%.0f,%.0f" % tuple(bg_mean), ratio, verdict))

print("\n  样张目录 %s（含底部渐变与占位标题，可直接眼检）" % OUT)
print("  判定标准：浅色标题字对比度 ≥4.5 为 AA")
