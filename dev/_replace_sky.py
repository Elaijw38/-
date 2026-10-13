# -*- coding: utf-8 -*-
"""替换 01 天象小地图为修订版，并做与其他四张相同的机械核查。

修订原因：初版天象"一般"——一条水平线把画面切成上下两半，
日、月、云、雨、火、山、人各占一处，是**并列陈列**而不是一个场景；
祭火太小、前景大片空沙地。修订版给了一个真正的主体：
巨大的日轮居中，烟柱自祭坛直上没入日面，云自左侧层叠压来、
右侧落雨挂月牙——天地由一根烟连成一体。

核查项与他图一致：尺寸、左上角/底部带是否留净（要叠编号与名称）、
中心是否够"值得探索"。
"""
import os

import numpy as np
from PIL import Image

DST = r"C:\DSH\字趣\out\minimaps"
SRC = r"C:\Users\32058\.dsh\profiles\desktop\task_6xD0TJ1LN7JaTcrV9gHzDxMGPcsRpYBq.png"
OUT = os.path.join(DST, "minimap-01-天象.jpg")
TARGET = (2624, 1472)


def detail(img, box):
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("L").crop((x0, y0, x1, y1)), dtype=np.float32)
    return float(a.std())


im = Image.open(SRC).convert("RGB")
if im.size != TARGET:
    ar = im.size[0] / float(im.size[1])
    if abs(ar - TARGET[0] / float(TARGET[1])) > 0.01:
        raise SystemExit("!! 宽高比不是 16:9：%s" % (im.size,))
    im = im.resize(TARGET, Image.LANCZOS)
im.save(OUT, "JPEG", quality=93, optimize=True)

W, H = im.size
tl = detail(im, (0, 0, int(W * 0.18), int(H * 0.14)))
bt = detail(im, (0, int(H * 0.84), W, H))
ce = detail(im, (int(W * 0.30), int(H * 0.28), int(W * 0.70), int(H * 0.72)))
flag = ""
if tl > 42:
    flag += " 左上偏花"
if bt > 42:
    flag += " 底部偏花"
if ce < 12:
    flag += " 中心偏空"

print("  01 天象（修订）  %dx%d" % (W, H))
print("    左上角 %.1f   底部带 %.1f   中心 %.1f%s" % (tl, bt, ce, flag or "   OK"))
print("    %s  %d KB" % (OUT, os.path.getsize(OUT) // 1024))
