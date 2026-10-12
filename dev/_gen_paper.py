# -*- coding: utf-8 -*-
"""纸张纤维改用一张真正的纹理图。

之前想用 CSS 内联的 feTurbulence SVG 当纸纹，浏览器始终判为非法
（单独渲染那个 SVG 是好的，但作为 CSS 背景的 data URI 就是 backgroundImage: none，
各种编码方式都试过）。不再纠缠，生成一张可平铺的纸纹 PNG：

  · 256×256，可无缝平铺（噪声按环面取样，边缘不会出现接缝）
  · 多频叠加：低频给"云斑"，高频给"纤维颗粒"
  · 对比压得极低（±10 灰阶左右）——是手感，不是花纹

体积上噪声图不好压，但只有一张、且会被缓存，可以接受。
"""
import os
from PIL import Image, ImageFilter
import random

OUT = r"C:\DSH\字趣\assets\paper.png"
S = 256
rnd = random.Random(20250412)      # 固定种子，纹理每次生成都一样

# 低频：稀疏暗点 → 高斯模糊成云斑；按环面铺 9 份保证左右上下无缝
low = Image.new("L", (S, S), 128)
px = low.load()
for _ in range(180):
    x, y = rnd.randrange(S), rnd.randrange(S)
    px[x, y] = 128 + rnd.randint(-60, 60)
# 环面平铺后模糊
big = Image.new("L", (S * 3, S * 3), 128)
for dy in range(3):
    for dx in range(3):
        big.paste(low, (dx * S, dy * S))
big = big.filter(ImageFilter.GaussianBlur(S * 0.22))
low = big.crop((S, S, S * 2, S * 2))

# 高频：逐像素细颗粒
hi = Image.new("L", (S, S))
hp = hi.load()
for y in range(S):
    for x in range(S):
        hp[x, y] = 128 + rnd.randint(-16, 16)

# 合成：低频权重小，高频权重大；整体再压低对比
out = Image.new("L", (S, S))
op, lp, hpp = out.load(), low.load(), hi.load()
for y in range(S):
    for x in range(S):
        v = 128 + (lp[x, y] - 128) * 0.42 + (hpp[x, y] - 128) * 0.75
        op[x, y] = max(0, min(255, int(round(v))))

# 先把自身动态范围拉满，再映到 [234, 255]：
# multiply 时最多暗 8% —— 看得见是纸，又不至于变成花纹。
lo0, hi0 = out.getextrema()
span = max(1, hi0 - lo0)
out = out.point(lambda v: int(round(234 + ((v - lo0) / float(span)) * 21)))
out.convert("RGB").save(OUT, "PNG", optimize=True)
print("  已生成 %s  %dx%d  %d KB" % (OUT, S, S, os.path.getsize(OUT) // 1024))
lo, hi2 = out.getextrema()
print("  灰阶范围 %d~%d（255 为纯白；越接近 255 越淡）" % (lo, hi2))
