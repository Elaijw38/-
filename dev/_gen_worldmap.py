# -*- coding: utf-8 -*-
"""生成「甲骨寻字秘境」大地图底图的最终尺寸版，以及五块区域显影层。

分工（为什么这么做）：
  · 底图是一整张手绘艺术稿（图像模型出图），裁到 1800×1010。
  · 五块显影层**不能也靠出图**——五次独立出图无法保证彼此与底图
    像素级对齐，而"学完一小块就显出大地图上对应的那一片"要求严丝合缝。
    所以显影层的**几何在这里按真实节点坐标算**（App.levels.map.zones
    的 objects x/y，就是网页上那 61 个热区的坐标），
    再做出"已探索"的发光观感。每一块因此永远贴着它真正覆盖的那批节点。

区域形状为什么用 metaball（而不是一个椭圆）：
  第一版我给每块区域拟合了一个大椭圆，结果半径涨到半张画布
  ——四角不透明（实测角上 alpha 79/45），叠上去会糊住整张底图。
  原因是节点本身是散开的，单个椭圆必然被拉爆。
  改成：每个节点落一个高斯影响核，全场求和后阈值化。
  聚在一起的节点自然连成一片，散开的节点各自成岛；
  阈值上再叠低频噪声，边缘就是不规则的、有机的，
  而且**节点到不了的地方永远透明**（四角自然干净）。

产出：
  out/world-map.png                 大地图底图      1800×1010
  out/world-map-reveal-1..5-*.png   五块显影层      1800×1010 RGBA 透明
  out/reveal-preview.png            叠在底图上的对照图（自查用）

显影的观感是"照亮"而不是"盖色"：暗部完全透明，亮部才提亮+染色，
所以叠上去，已探索区会**亮起来**，其余地方原样不动。
"""
import io
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO = r"C:\DSH\字趣"
SRC_MAP = r"C:\Users\32058\.dsh\profiles\desktop\task_EGVmFpbJpQJ7GPBfHrRr3ctcUMypjki9.png"
OUT = os.path.join(REPO, "out")

W, H = 1800, 1010          # 要求的底图尺寸

# 区域主色：偏亮、低饱和的"已探索"色，压在暗底图上要跳得出来
ZONE_TINT = {
    "sky":   (236, 214, 152),   # 天象：月白偏金
    "land":  (170, 216, 226),   # 山川：水青
    "plant": (176, 216, 150),   # 草木：藤绿
    "beast": (238, 196, 138),   # 禽兽虫鱼：赭
    "life":  (244, 202, 158),   # 人居器物：陶金
}


def load_zones():
    t = io.open(os.path.join(REPO, "js", "core", "_data.js"), encoding="utf-8").read()
    i = t.index("App.levels = ")
    j = t.index(";\n", i)
    return json.loads(t[i + len("App.levels = "):j])["map"]["zones"]


# --------------------------------------------------------------- 低频噪声
def value_noise(w, h, cells, seed):
    """值噪声：小网格随机 + 双三次放大，得到平滑的低频起伏（0..1）。"""
    r = random.Random(seed)
    gw, gh = max(2, w // cells + 2), max(2, h // cells + 2)
    g = np.array([[r.random() for _ in range(gw)] for _ in range(gh)], dtype=np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8), "L").resize((w, h), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255.0


# --------------------------------------------------------------- 区域掩膜
def zone_mask(objects, seed, grow=1.0):
    """由节点位置算出一块含混的覆盖区域。

    返回 (mask, hard)：
      mask  0..1 羽化后的掩膜，给发光观感用
      hard  0/1 硬边界（阈值化后未羽化），**用来把 alpha 清零**。
            必须靠它保证"节点到不了的地方彻底透明"——
            只靠羽化过的 mask，高斯模糊会把 alpha 甩到四角去（实测角上 46）。
    """
    # 在低分辨率网格上算 metaball：快，且天然平滑
    w, h = W // 2, H // 2
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    xs *= 2.0
    ys *= 2.0

    field = np.zeros((h, w), dtype=np.float32)
    for o in objects:
        # 每个节点的影响半径：跟随它自己的热区半径，并留出余量
        R = max(150.0, float(o.get("r", 30)) * 5.0) * grow
        dx = xs - float(o["x"])
        dy = ys - float(o["y"])
        field += np.exp(-(dx * dx + dy * dy) / (2.0 * R * R))

    f = field / max(1e-6, field.max())
    # 阈值：叠两层低频噪声，让边界不要平滑得像等高线
    for cells, amp, sd in ((150, 0.30, seed + 1), (52, 0.16, seed + 2)):
        f = f + amp * (value_noise(w, h, cells, sd) - 0.5)

    TH = 0.34
    hard = (f >= TH).astype(np.uint8) * 255
    soft = np.clip((f - TH) / (TH * 1.25), 0.0, 1.0) * 255.0

    to_big = lambda arr: Image.fromarray(arr.astype(np.uint8), "L").resize(
        (W, H), Image.BICUBIC)
    hard_im = to_big(hard).filter(ImageFilter.MaxFilter(3))   # 闭一下小孔
    hard_f = (np.asarray(hard_im, dtype=np.float32) / 255.0 > 0.5).astype(np.float32)

    # 画布四周留一圈安全边：显影层不许贴到裁切线上。
    # 天象那批节点最高只到 y=88，它的 blob 会顶到画面上缘，
    # 在裁切线那里出现一条亮带，看着像渲染坏了。
    # 但**必须是渐隐，不能直接清零**——硬清零会在画面上切出一条笔直的边
    # （试过，看起来像 bug 而不像设计）。
    M, FADE = 26, 150
    ramp_x = np.clip(np.minimum(np.arange(W), W - 1 - np.arange(W)) / float(FADE), 0, 1)
    ramp_y = np.clip(np.minimum(np.arange(H), H - 1 - np.arange(H)) / float(FADE), 0, 1)
    hard_f = hard_f * (ramp_y[:, None] ** 0.8) * (ramp_x[None, :] ** 0.8)
    hard_f[:M, :] = 0.0
    hard_f[-M:, :] = 0.0
    hard_f[:, :M] = 0.0
    hard_f[:, -M:] = 0.0

    # 羽化必须**朝内**做，不能朝外：高斯模糊会把 alpha 甩到区域之外，
    # 那样一块显影层就会糊到别人家的地盘上。所以做法是——
    #   内部柔化（让区域里外有层次） 再 **乘回硬边界**，边界即最外侧。
    inner_soft = np.asarray(to_big(soft), dtype=np.float32) / 255.0
    mask = np.clip(inner_soft, 0.0, 1.0) * hard_f
    return mask, hard_f


# --------------------------------------------------------------- 发光层
def build_reveal(mask, tint, seed):
    """把掩膜做成一团**光**：内部提亮 + 边界更亮一圈 + 叶脉光丝 + 细颗粒。

    颜色必须往**亮**里走。第一版把 RGB 定成"区域主色 × 亮度"，
    主色本身偏中等亮度（约 0.7），alpha 又压在 0.9 左右，
    于是普通 alpha 合成算出来是**压暗**——实测每个区域都 -11 ~ -18 亮度。
    "显影"要的是亮起来，所以这里：
      · RGB 定成接近白的热色（只带一点区域色偏），往 1.0 抬
      · 中心最亮、边界次之，靠 ring 在阈值附近再抬一道"光路"
      · alpha 完全由 mask 决定，mask=0 的地方连 RGB 一起归零
    """
    r = random.Random(seed)

    # 光要**集中**，不能漫开。
    # 第一版让亮度大面积铺在 0.5~0.9，结果叠上去是一层奶白雾，
    # 把地貌全糊平了——那既不像"已探索"，也不像"值得探索"。
    # 现在收成：核心亮、外圈迅速回落到几乎不亮，
    # 地貌看得见，只在被点亮的地方透出一层暖金。
    # pow 3 让亮部只占区域的一小块；0.30 是外围残留的暖调，避免"贴纸感"。
    core = np.clip(mask, 0.0, 1.0) ** 3.0
    ring = np.exp(-((mask - 0.30) ** 2) / (2 * 0.13 ** 2))     # 内圈一道光路
    lum = np.clip(core * 0.85 + ring * 0.34, 0.0, 1.0)

    # 光丝：区域里散开的细亮线，像被点亮的路径。
    # 这一层**必须有**——只靠亮度包络，一块显影层就是一个平面的色斑
    # （试过：看起来像纸上挖了个洞，不像"这里值得探索"）。
    vein = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vein)
    mimg = Image.fromarray((mask * 255).astype(np.uint8), "L")
    tries = 0
    drawn = 0
    while drawn < 260 and tries < 6000:
        tries += 1
        x = r.uniform(0, W)
        y = r.uniform(0, H)
        if mimg.getpixel((int(x) % W, int(y) % H)) < 120:
            continue
        drawn += 1
        ang = r.uniform(0, 2 * math.pi)
        seg = [(x, y)]
        ln = r.uniform(80, 300)
        n = 7
        for s in range(1, n + 1):
            t = s / float(n)
            ang += r.uniform(-0.30, 0.30)
            seg.append((x + math.cos(ang) * ln * t, y + math.sin(ang) * ln * t))
        vd.line(seg, fill=r.randint(150, 255), width=max(1, int(r.uniform(1, 3))))
    vein = np.asarray(vein.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
    lum = np.clip(lum + vein * 0.55 * mask, 0.0, 1.0)

    # 细颗粒（星点）
    gr = (np.random.default_rng(seed).random((H, W)).astype(np.float32) - 0.5) * 0.10
    lum = np.clip(lum + gr * (mask > 0.2), 0.0, 1.0)

    # --- 光色与不透明度 ---------------------------------------------------
    # 这里连踩两个坑，都记下来：
    #
    # 坑一：颜色必须近乎白。普通 alpha 合成 out = rgb*a + base*(1-a)，
    #       要 out > base 就得 rgb > base（底图约 0.46）。
    #       第一版 rgb 取 0.40~0.65，于是每个区域都被**压暗**。
    #
    # 坑二（真正致命的）：PIL 存的是**直存 alpha（straight）**，
    #       合成时自己会乘一次 a。我却又在数据里把 rgb 预乘了一遍 a，
    #       结果 a 被乘了两次 —— 实测导出像素的 R=G=B=A=140，
    #       也就是"近白"变成了 0.55 的中灰，怎么调都亮不起来。
    #       所以：**rgb 一律直存，不要预乘**。
    tint_a = np.array(tint, dtype=np.float32) / 255.0
    gold = 0.35 * tint_a + 0.65 * np.array([1.0, 0.93, 0.74], dtype=np.float32)
    light = 0.90 + 0.10 * np.clip(gold, 0.0, 1.0)      # 近白，只带一点金色偏

    vein3 = vein[..., None]
    # 光丝处更白更亮，亮线才跳得出来；不预乘 alpha
    rgb = np.clip(light[None, None, :] + vein3 * 0.10 * mask[..., None], 0.0, 1.0)

    # alpha：核心实、外圈透。上限 0.55，因为光色近白，这个量已足够明显提亮，
    # 同时地貌还透得出来（不会糊成一块奶白）。
    alpha = np.clip(mask, 0.0, 1.0) ** 1.5 * 0.55

    out = np.concatenate([rgb, alpha[..., None]], axis=2)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")


# --------------------------------------------------------------- 主流程
os.makedirs(OUT, exist_ok=True)

# 1) 底图：等比裁到 1800×1010
src = Image.open(SRC_MAP).convert("RGB")
sw, sh = src.size
target_ar = W / float(H)
if sw / float(sh) > target_ar:
    nw = int(round(sh * target_ar))
    x0 = (sw - nw) // 2
    src = src.crop((x0, 0, x0 + nw, sh))
else:
    nh = int(round(sw / target_ar))
    y0 = (sh - nh) // 2
    src = src.crop((0, y0, sw, y0 + nh))
base = src.resize((W, H), Image.LANCZOS)
p_base = os.path.join(OUT, "world-map.png")
base.save(p_base, "PNG", optimize=True)
print("  base   world-map.png  %dx%d  %d KB" % (W, H, os.path.getsize(p_base) // 1024))

# 2) 五块显影层
zones = load_zones()
layers = []
for i, z in enumerate(zones):
    mask, hard = zone_mask(z["objects"], seed=500 + i * 91)
    tint = ZONE_TINT.get(z["id"], (238, 210, 160))
    rgba = build_reveal(mask, tint, seed=900 + i * 47)
    p = os.path.join(OUT, "world-map-reveal-%d-%s.png" % (i + 1, z["id"]))
    rgba.save(p, "PNG", optimize=True)
    layers.append(rgba)
    cov = float(hard.mean()) * 100.0
    print("  reveal %d %-6s %-8s nodes %2d  cover %4.1f%%  %d KB"
          % (i + 1, z["id"], z["name"], len(z["objects"]), cov,
             os.path.getsize(p) // 1024))

# 3) 对照预览
prev = base.convert("RGBA")
for L in layers:
    prev = Image.alpha_composite(prev, L)
p_prev = os.path.join(OUT, "reveal-preview.png")
prev.convert("RGB").save(p_prev, "PNG", optimize=True)
print("  preview reveal-preview.png  %d KB" % (os.path.getsize(p_prev) // 1024))
