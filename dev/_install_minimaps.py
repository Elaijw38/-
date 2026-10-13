# -*- coding: utf-8 -*-
"""装入五张修订版小地图 + 把两处 UI 叠加区做成"安全的"。

为什么不是单纯压暗：
  底部要叠地图标题、左上角要叠 UI 位。实测发现**均匀压暗不会降低
  "细节量"指标**（标准差对整体乘系数是不变的：std(k·x)=k·std(x)，
  k<1 时反而更接近 0，但相对起伏比例不变），所以上一版压完 01 仍是 50.1。
  真正有效的是**降低该区域的对比**——轻微模糊 + 渐隐。
  模糊只作用在叠加带内、且强度由 0 渐增，边界看不出接缝。

两处处理：
  · 底部 16%：轻微模糊（最多约 3px）+ 暖墨渐隐，给标题让路
  · 左上角：轻微模糊 + 极淡提亮，给地图编号让路
  两者都只在边缘生效，主体一律不动。
"""
import os

import numpy as np
from PIL import Image, ImageFilter

REPO = r"C:\DSH\字趣"
DST = os.path.join(REPO, "out", "minimaps")
SRC = r"C:\Users\32058\.dsh\profiles\desktop"
W, H = 2624, 1472

BOTTOM_FROM = 0.84      # 底部由 84% 开始处理
BOTTOM_BLUR = 3.0       # 最多模糊 3px
BOTTOM_INK = 150 / 255.0
CORNER_W, CORNER_H = 0.20, 0.16   # 左上角处理范围
CORNER_BLUR = 2.5
CORNER_LIFT = 0.10      # 极淡提亮，让叠上去的编号更清楚
INK = np.array([38, 30, 22], dtype=np.float32)
PAPER = np.array([242, 232, 213], dtype=np.float32)

ITEMS = [
    ("01", "天象",     "task_dqjXdLHlzKM6cY5kDrYZ8fIXfXKb7N0C.png"),
    ("02", "山川",     "task_NwtIe6svQa2mY5MvVYjTxCZN7XfspLAQ.png"),
    ("03", "草木",     "task_EROCoNmI4q8xiOHVyKJJdEP3q9Zxw8vl.png"),
    ("04", "禽兽虫鱼", "task_WZt0RHjoec0NXfgn2rPCYddddQ0xr85O.png"),
    ("05", "人居器物", "task_fXjl98fXsODW1kPaylRsmp7rYsCMBqTk.png"),
]


def detail(img, box):
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("L").crop((x0, y0, x1, y1)), dtype=np.float32)
    return float(a.std())


def soften(im):
    """底部 + 左上角两处 UI 叠加带做降对比处理。"""
    a = np.asarray(im, dtype=np.float32)

    # —— 底部：渐增模糊 + 暖墨渐隐 ——
    y0 = int(H * BOTTOM_FROM)
    t = np.clip((np.arange(H) - y0) / float(H - y0), 0.0, 1.0)
    ramp = np.zeros((H, 1, 1), dtype=np.float32)
    ramp[:, 0, 0] = (t ** 1.6) * BOTTOM_INK
    a = a * (1.0 - ramp) + INK[None, None, :] * ramp

    # 模糊：整图轻微模糊一份，再按纵向权重混回底部
    blur_b = np.asarray(im.filter(ImageFilter.GaussianBlur(BOTTOM_BLUR)), dtype=np.float32)
    wb = ((t ** 1.2) * 0.9)[:, None, None]
    a = a * (1.0 - wb) + blur_b * wb

    # —— 左上角：渐增模糊 + 极淡提亮（给地图编号让路）——
    xs = np.arange(W)[None, :].astype(np.float32)
    ys = np.arange(H)[:, None].astype(np.float32)
    dx = np.clip(1.0 - xs / (W * CORNER_W), 0.0, 1.0)
    dy = np.clip(1.0 - ys / (H * CORNER_H), 0.0, 1.0)
    wc = (dx * dy) ** 1.3                          # 左上角为 1，向外衰减
    blur_c = np.asarray(im.filter(ImageFilter.GaussianBlur(CORNER_BLUR)), dtype=np.float32)
    wc3 = (wc * 0.85)[..., None]
    a = a * (1.0 - wc3) + blur_c * wc3
    lift = (wc * CORNER_LIFT)[..., None]
    a = a * (1.0 - lift) + PAPER[None, None, :] * lift

    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


print("  %-4s %-10s %-9s %-8s %-8s %s" % ("no", "主题", "尺寸", "左上角", "底部带", "中心"))
print("  " + "-" * 64)

thumbs = []
for no, name, fn in ITEMS:
    im = Image.open(os.path.join(SRC, fn)).convert("RGB")
    ar = im.size[0] / float(im.size[1])
    if abs(ar - W / float(H)) > 0.01:
        if ar > W / float(H):
            nw = int(round(im.size[1] * W / float(H)))
            x0 = (im.size[0] - nw) // 2
            im = im.crop((x0, 0, x0 + nw, im.size[1]))
        else:
            nh = int(round(im.size[0] * H / float(W)))
            y0 = int((im.size[1] - nh) / 2)
            im = im.crop((0, y0, im.size[0], y0 + nh))
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)

    im = soften(im)
    p = os.path.join(DST, "minimap-%s-%s.jpg" % (no, name))
    im.save(p, "JPEG", quality=93, optimize=True)

    tl = detail(im, (0, 0, int(W * 0.18), int(H * 0.14)))
    bt = detail(im, (0, int(H * 0.84), W, H))
    ce = detail(im, (int(W * 0.30), int(H * 0.28), int(W * 0.70), int(H * 0.72)))
    flag = (" 左上偏高" if tl > 42 else "") + (" 底部偏高" if bt > 42 else "") + (" 中心偏空" if ce < 12 else "")
    print("  %-4s %-10s %-9s %-8.1f %-8.1f %.1f%s"
          % (no, name, "%dx%d" % im.size, tl, bt, ce, flag or "   OK"))
    thumbs.append(im)

for tw, th, nm, tag in ((520, 292, "minimaps-overview.jpg", "拼图预览"),
                        (240, 135, "minimaps-overview-thumb.jpg", "缩略预览")):
    sheet = Image.new("RGB", (tw * 5, th), (242, 232, 213))
    for i, im in enumerate(thumbs):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (i * tw, 0))
    p = os.path.join(REPO, "out", nm)
    sheet.save(p, "JPEG", quality=92, optimize=True)
    print("\n  %s %s  %dx%d  %d KB" % (tag, p, sheet.size[0], sheet.size[1],
                                       os.path.getsize(p) // 1024))
