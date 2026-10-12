# -*- coding: utf-8 -*-
"""骨材质：生成一张可平铺的骨纹 PNG。

为什么需要它：上一版把"骨"做成了一张**平的米色纸**——低饱和、无纹理、
无斑驳，于是又素又空。真实的甲骨是一件**物件**：骨面深浅不匀、有纵向骨纹、
有褐斑、有虫蛀的小孔与凹坑。这些不是"装饰花纹"，是骨之所以为骨的东西。

做法（与 dev/_gen_paper.py 同一套思路，但内容换成骨的）：
  · 512×512，可无缝平铺（低频噪声与斑块一律按环面 / 越界回卷绘制）
  · 低频：大块深浅不匀（bone 本身的颜色就是不匀的）
  · 骨纹：纵向的胶原纤维条带，宽窄不一、断续
  · 褐斑：主轴偏竖的拉长斑块（--patina / --patina-2）
  · 虫蛀：一批深色小孔 + 一小撮带亮边的凹坑（--pit）
  · 颗粒：逐像素细颗粒

亮度口径很重要：这张图会以 **multiply** 压在骨色底上，
所以它越白越"不存在"，越暗越明显。基准定在 246（≈ --bone 的亮度），
平均压到 0.94 上下——是"手感与斑驳"，不是"花纹"。

用法见 css/theme.css 的 --bone-tex 令牌。
"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter

OUT = r"C:\DSH\字趣\assets\bone.png"
S = 512
rnd = random.Random(20250412)          # 固定种子：纹理每次生成都一样

BASE = 246        # 基准亮（≈ --bone #f2e8d5 的亮度 236 再抬一点，压得轻）
GRAIN = 7         # 高频颗粒幅度


# ---------------------------------------------------------------- 工具
def torus_noise(side, blobs, blur, lo, hi, r):
    """稀疏散点 → 高斯模糊 → 环面裁回，得到左右上下无缝的云斑。

    side 必须能整除 S，否则裁回时接缝对不上。"""
    n = S // side
    small = Image.new("L", (n, n), 128)
    px = small.load()
    for _ in range(blobs):
        x, y = r.randrange(n), r.randrange(n)
        px[x, y] = 128 + r.randint(lo, hi)
    big = Image.new("L", (n * 3, n * 3), 128)
    for dy in range(3):
        for dx in range(3):
            big.paste(small, (dx * n, dy * n))
    big = big.filter(ImageFilter.GaussianBlur(side * (blur / float(S))))
    return big.crop((n, n, n * 2, n * 2)).resize((S, S), Image.BILINEAR)


def wrap_rect(d, x, y, w, h, fill):
    """越界回卷地画一个矩形，保证平铺时跨边界的斑块不断裂。"""
    for oy in (-S, 0, S):
        for ox in (-S, 0, S):
            d.rectangle([x + ox, y + oy, x + ox + w, y + oy + h], fill=fill)


def wrap_ellipse(d, x, y, w, h, fill, outline=None, width=1):
    for oy in (-S, 0, S):
        for ox in (-S, 0, S):
            d.ellipse([x + ox, y + oy, x + ox + w, y + oy + h],
                      fill=fill, outline=outline, width=width)


def blend(a, b, t):
    """按 t 把 b 混进 a。"""
    return Image.blend(a, b, t)


def layer_from_noise(noise, dark_at, light_at, gamma=1.0):
    """把 0..255 的噪声映射成一张以亮色为底、暗处为斑的层。

    noise 值高 → 取 dark_at（更暗），值低 → 取 light_at。"""
    def f(v):
        t = (v / 255.0) ** gamma
        return int(round(light_at + (dark_at - light_at) * t))
    return noise.point(f)


# ---------------------------------------------------------------- 1) 底色不匀
# 低频斑块必须**大而明显**：铺成整页背景时，细而淡的东西会被浏览器"平均"掉，
# 远看就只剩一层灰噪点——那是"脏"，不是"骨"。所以这里宁可少而大、对比拉足。
mottle = torus_noise(128, 16, 62, -95, 95, rnd)
uneven = layer_from_noise(mottle, dark_at=196, light_at=253, gamma=1.0)

# ---------------------------------------------------------------- 2) 骨纹（纵向条带）
# 条带必须**完全落在 0..S 之内**：一旦某条跨过 S 边界，平铺时它会被硬切一刀，
# 接缝就露出来了（上一版就是这么露的，横向接缝差 13.2 而图内只有 2.9）。
stri = Image.new("L", (S, S), 252)
sd = ImageDraw.Draw(stri)
x = rnd.randint(8, 40)                 # 起点随机，但条带只画在 tile 内
while x < S - 22:
    w = min(rnd.randint(12, 32), S - 10 - x)   # 宽条：细条在整页尺度上会被平均掉
    if w < 10:
        break
    if rnd.random() < 0.82:
        # 断续：一条骨纹分几段画。**每段的宽窄与深浅都各自抖一下**——
        # 否则一列等宽的矩形铺开来像瓦楞纸，不像骨（上一版就是这么露的马脚）。
        y = rnd.randint(-20, 20)
        while y < S:
            seg = rnd.randint(50, 200)
            dw = rnd.randint(-4, 4)
            x0 = x + rnd.randint(-3, 3)
            w0 = max(3, w + dw)
            sd.rounded_rectangle([x0, y, x0 + w0, y + seg],
                                 radius=rnd.randint(2, 7),
                                 fill=rnd.randint(184, 230))
            y += seg + rnd.randint(20, 90)
    x += w + rnd.randint(8, 30)
stri = stri.filter(ImageFilter.GaussianBlur(3.0))

# ---------------------------------------------------------------- 3) 褐斑（拉长的斑块）
pat = Image.new("L", (S, S), 253)
pd = ImageDraw.Draw(pat)
for _ in range(64):                    # 少一些、大一些
    w = rnd.randint(20, 88)
    h = int(w * rnd.uniform(1.4, 3.6))      # 主轴偏竖：顺着骨纹方向
    x = rnd.randrange(-w, S)
    y = rnd.randrange(-h, S)
    wrap_ellipse(pd, x, y, w, h, fill=rnd.randint(196, 228))
pat = pat.filter(ImageFilter.GaussianBlur(7.0))

# ---------------------------------------------------------------- 4) 虫蛀 / 凹坑
pit = Image.new("L", (S, S), 252)
kd = ImageDraw.Draw(pit)
for _ in range(96):                        # 细密的深色小孔
    d0 = rnd.randint(3, 7)
    wrap_ellipse(kd, rnd.randrange(S), rnd.randrange(S), d0, d0,
                 fill=rnd.randint(178, 214))
pits_big = []
for _ in range(10):                        # 稍大的凹坑（带亮边，才像坑不像污点）
    d0 = rnd.randint(9, 17)
    x, y = rnd.randrange(S), rnd.randrange(S)
    pits_big.append((x, y, d0))
    wrap_ellipse(kd, x, y, d0, d0, fill=rnd.randint(160, 190))
pit = pit.filter(ImageFilter.GaussianBlur(0.9))
# 亮边：在凹坑外圈描一圈比底还亮的边（骨屑翻起处）
rim = Image.new("L", (S, S), 255)
rd = ImageDraw.Draw(rim)
for (x, y, d0) in pits_big:
    wrap_ellipse(rd, x - 1, y - 1, d0 + 2, d0 + 2, fill=255, outline=253, width=2)
rim = rim.filter(ImageFilter.GaussianBlur(0.8))

# ---------------------------------------------------------------- 5) 合成
# 叠序与权重是有讲究的，别随手改：
#   · uneven 用斑点噪声把自身动态范围**铺满**了，任何后叠的层若权重不够，
#     都会被它"平均"掉（骨纹连叠两版都看不见，就是这个原因）。
#   · 所以骨纹的权重给到 .90，让竖直的骨纹成为**主结构**；
#   · 褐斑 .28 只做局部加深，孔洞 .55 收着用——孔太多会变成"发霉的纸"。
out = uneven.copy()
out = blend(out, stri, 0.90)
out = blend(out, pat, 0.28)
out = blend(out, pit, 0.55)
out = blend(out, rim, 0.30)                # 亮边抬一点点，凹坑才有立体感

# ---------------------------------------------------------------- 6) 归一化
# multiply 的下手轻重完全由这张图的亮度决定，所以这里**直接按目标均值定标**。
#
# 走过的弯路记在这儿，免得下次再踩：
#   · 先按自身动态范围拉满 → 各层叠加后的总亮度会漂，量出来只压暗 3.8%，等于白做；
#   · 再用 gamma 二分 + 增益 → gamma 顶到上界后直方图挤在 0/255 两端，
#     乘增益几乎改不动均值（151 张里绝大多数是 255，乘 0.97 还是 255）。
# 所以：用**减偏移**，它对均值是一比一的作用，不受直方图形状影响。
TARGET_DARK = 0.078     # 目标：平均把骨色压暗 7.8%
GAMMA = 0.85            # 中间调反差：让斑驳读得出来，但不变成花纹

ND = list(out.getdata())
target_mean = 255.0 * (1.0 - TARGET_DARK)
lm = [int(round(255.0 * ((v / 255.0) ** GAMMA))) for v in range(256)]
cur = sum(lm[v] for v in ND) / float(S * S)
offset = target_mean - cur
out = out.point([max(0, min(255, int(round(lm[v] + offset)))) for v in range(256)])
print("  定标 gamma %.2f  偏移 %+.2f（%s）"
      % (GAMMA, offset, "压暗" if offset < 0 else "提亮"))

# 颗粒最后加：此时亮度口径已定，颗粒幅度是多少就压多少，不再被归一化放大
gp = out.load()
for y in range(S):
    for x in range(S):
        v = gp[x, y] + rnd.randint(-GRAIN, GRAIN)
        gp[x, y] = 0 if v < 0 else (255 if v > 255 else v)

# 灰度图（三层都只用亮度）——比 RGB 小三成
out.convert("L").save(OUT, "PNG", optimize=True)

# ---------------------------------------------------------------- 7) 自检
im = out
lo, hi = im.getextrema()
data = list(im.getdata())
mean = sum(data) / float(S * S)
print("  已生成 %s  %dx%d  %d KB" % (OUT, S, S, os.path.getsize(OUT) // 1024))
print("  灰阶 %d~%d  均值 %.1f  →  以 multiply 压骨色时平均压暗 %.1f%%"
      % (lo, hi, mean, (1 - mean / 255.0) * 100))

# 接缝自检：量左/右边缘列与上/下边缘行的平均差，跟图内部相邻列做对照。
# 无缝时接缝差应当落在"图内相邻列"的同一量级上。


def col(px, x):
    return [px[y * S + x] for y in range(S)]


def row(px, y):
    return px[y * S:(y + 1) * S]


diff_lr = sum(abs(a - b) for a, b in zip(col(data, S - 1), col(data, 0))) / float(S)
diff_tb = sum(abs(a - b) for a, b in zip(row(data, S - 1), row(data, 0))) / float(S)
inner = sum(abs(a - b) for a, b in zip(col(data, S // 2), col(data, S // 2 + 1))) / float(S)
print("  接缝 左右 %.2f / 上下 %.2f （图内相邻列典型 %.2f）→ %s"
      % (diff_lr, diff_tb, inner,
         "无缝" if diff_lr <= inner * 2.5 and diff_tb <= inner * 2.5 else "有缝 X"))
