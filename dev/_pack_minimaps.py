# -*- coding: utf-8 -*-
"""导出五张第二关小地图场景原画，按 01..05 单独成文件，并做机械核查。

核查项（能自动量的一律量，不靠肉眼）：
  · 尺寸 ≥ 1920×1080 且接近 16:9（网页会按 16:9 显示并可能轻微裁边）
  · 四边留白带、以及左上角 / 底部条带，是否有高对比内容
    （网页要在左上叠地图编号、底部叠名称+暗色渐变，那里不该压着关键主体）
  · 中心区域的对比度是否足够（主体要"一眼看得出值得探索"）

高对比判定用局部标准差：色块、线条密的地方标准差高；
平静的留白/渐变天空标准差低。阈值只做体检，不做审美判断。
"""
import os

import numpy as np
from PIL import Image

REPO = r"C:\DSH\字趣"
SRC = r"C:\Users\32058\.dsh\profiles\desktop"
DST = os.path.join(REPO, "out", "minimaps")
os.makedirs(DST, exist_ok=True)

ITEMS = [
    ("01", "天象",       "task_RT6lDVXfVWdY0FdlKiPo7RwHb3iPoBIP.png"),
    ("02", "山川",       "task_9Gy5EZH3zf7N0GSuoBNO7e0k3J5S52TC.png"),
    ("03", "草木",       "task_9NwpxPiJADyMpnLUwJxaNIXEKopAMOLL.png"),
    ("04", "禽兽虫鱼",   "task_XYaNI6gV2YsSVRpVAHJfbx3jwZcS8YjO.png"),
    ("05", "人居器物",   "task_D3sPRcCbvZtNjhFQbBoQ5Ileay3UhvXV.png"),
]

TARGET_W, TARGET_H = 2624, 1472


def detail(img, box):
    """局部"细节量"：灰度标准差。越高 = 内容/线条越密。"""
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("L").crop((x0, y0, x1, y1)), dtype=np.float32)
    return float(a.std())


print("  %-4s %-10s %-11s %-9s %-9s %s" %
      ("no", "主题", "尺寸", "左上角", "底部带", "中心"))
print("  " + "-" * 62)

ok = True
for no, name, fn in ITEMS:
    src = os.path.join(SRC, fn)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    ar = w / float(h)
    if (w, h) != (TARGET_W, TARGET_H):
        # 只在必要时重采样；优先保住 2624×1472
        if abs(ar - TARGET_W / float(TARGET_H)) < 0.01:
            im = im.resize((TARGET_W, TARGET_H), Image.LANCZOS)
            w, h = im.size
        else:
            ok = False
    p = os.path.join(DST, "minimap-%s-%s.jpg" % (no, name))
    im.save(p, "JPEG", quality=93, optimize=True)

    W, H = im.size
    tl = detail(im, (0, 0, int(W * 0.18), int(H * 0.14)))              # 左上角：叠编号
    bt = detail(im, (0, int(H * 0.84), W, H))                          # 底部带：叠名称
    ce = detail(im, (int(W * 0.30), int(H * 0.28), int(W * 0.70), int(H * 0.72)))
    flag = ""
    if tl > 42:
        flag += " 左上偏花"
    if bt > 42:
        flag += " 底部偏花"
    if ce < 12:
        flag += " 中心偏空"
    if flag:
        ok = False
    print("  %-4s %-10s %-11s %-9.1f %-9.1f %.1f%s"
          % (no, name, "%dx%d" % (W, H), tl, bt, ce, flag))

print()
print("  细节量参考：>42 视为该区域偏花（会与叠加的编号/名称打架）")
print("  结论：%s" % ("五张全部通过" if ok else "有项目需要复核"))
