# -*- coding: utf-8 -*-
"""出"统一地图风格"新版五图的拼图预览（先看构图与风格，暂不替换页面素材）。

出两版：
  · minimaps-mapstyle-overview.jpg        每张 520px 宽，看风格一致性
  · minimaps-mapstyle-overview-thumb.jpg  每张 240px 宽，看手机缩略识别度
另出一张"统一性体检"：逐张量
  · 有效场景占比（非纸白像素的比例）——太低说明大片空白
  · 底部带 / 左上角 细节量 —— 是否给 UI 叠加留了余地
  · 画面中心与四角的平均色 —— 五张是否落在同一色域
"""
import os

import numpy as np
from PIL import Image

REPO = r"C:\DSH\字趣"
SRC = r"C:\Users\32058\.dsh\profiles\desktop"
OUT = os.path.join(REPO, "out", "mapstyle")
os.makedirs(OUT, exist_ok=True)

# 本轮"地图风格"新版（01 / 02 为按构图反馈返修后的版本）
NEW = [
    ("01", "天象",     "task_ZDAe33Mv8aCj0vaj4Rj0kQpYrxuyNh3y.png"),
    ("02", "山川",     "task_pxvCzpgtkdOMsuczLDEDJ2OVN37stoEY.png"),
    ("03", "草木",     "task_XOFMrkZZ9dOTqugn2Iz98IxzwfSBq1c4.png"),
    ("04", "禽兽虫鱼", "task_4f09W3UCdWNgvfkmwrQCtqdBxtvJxbVF.png"),
    ("05", "人居器物", "task_YdpTZSPeZhDrfG8E4r8xAfSEHsF0XGd8.png"),
]
W, H = 2624, 1472


def detail(img, box):
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("L").crop((x0, y0, x1, y1)), dtype=np.float32)
    return float(a.std())


def scene_ratio(img):
    """有效场景占比：纸白（很亮的低饱和区域）之外的像素比例。"""
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    lum = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    paper = (lum > 205) & (sat < 26)
    return float(1.0 - paper.mean())


print("  %-4s %-10s %-9s %-9s %-8s %-8s %s"
      % ("no", "主题", "场景占比", "左上角", "底部带", "中心", "四角均色"))
print("  " + "-" * 78)

ims = []
for no, name, fn in NEW:
    im = Image.open(os.path.join(SRC, fn)).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    p = os.path.join(OUT, "mapstyle-%s-%s.jpg" % (no, name))
    im.save(p, "JPEG", quality=93, optimize=True)

    sr = scene_ratio(im)
    tl = detail(im, (0, 0, int(W * 0.18), int(H * 0.14)))
    bt = detail(im, (0, int(H * 0.85), W, H))
    ce = detail(im, (int(W * 0.30), int(H * 0.28), int(W * 0.70), int(H * 0.72)))
    a = np.asarray(im, dtype=np.float32)
    k = 130
    corners = np.concatenate([
        a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3),
        a[-k:, :k].reshape(-1, 3), a[-k:, -k:].reshape(-1, 3)])
    cm = corners.mean(axis=0)
    print("  %-4s %-10s %-9s %-9.1f %-8.1f %-8.1f %d,%d,%d"
          % (no, name, "%.1f%%" % (sr * 100), tl, bt, ce, cm[0], cm[1], cm[2]))
    ims.append(im)

for tw, th, nm, tag in ((520, 292, "minimaps-mapstyle-overview.jpg", "风格预览"),
                        (240, 135, "minimaps-mapstyle-overview-thumb.jpg", "缩略预览")):
    sheet = Image.new("RGB", (tw * 5, th), (242, 232, 213))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (i * tw, 0))
    p = os.path.join(REPO, "out", nm)
    sheet.save(p, "JPEG", quality=92, optimize=True)
    print("\n  %s %s  %dx%d  %d KB" % (tag, p, sheet.size[0], sheet.size[1],
                                       os.path.getsize(p) // 1024))
print("\n  单张新版在 %s" % OUT)
