# -*- coding: utf-8 -*-
"""把 9 张 AI 线稿压成与 assets/boss/ 一致的两色语言，并接入代用表。

为什么压两色：88 尊是「米色平涂 + 棕墨单线勾边、无阴影无渐变」，
而生成图是灰色厚涂+排线。与其反复调提示词，不如按**目标画风**做一次
确定性转换：取亮度做阈值 → 线条一个颜色、其余填米色、纸底透明。
这样 9 张和 88 尊在视觉上一定是同一套，不靠运气。
"""
import io
import json
import os

import numpy as np
from PIL import Image, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)

FILL = (244, 236, 220)      # 米色平涂（与 88 尊一致）
INK = (108, 76, 46)         # 棕墨线
JOBS = [
    ("b9-she_997101_.png", "89-she", "涉", "涉水怪"),
    ("b9-ming_997102_.png", "90-ming", "鸣", "鸣口怪"),
    ("b9-zhu_997103_.png", "91-zhu", "逐", "逐豕怪"),
    ("b9-an_997104_.png", "92-an", "安", "屋顶怪"),
    ("b9-jia_997105_.png", "93-jia", "家", "屋下豕怪"),
    ("b9-mu_997106_.png", "94-mu", "木", "树身怪"),
    ("b9-xiang_997107_.png", "95-xiang", "象", "长鼻象怪"),
    ("b9-gui_997108_.png", "96-gui", "龜", "巨龟怪"),
    ("b9-che_997109_.png", "97-che", "車", "双轮车怪"),
]

WHY = {
    "涉": "本关专属形象：涉水而行的长臂怪，水缠小腿——对应「涉」的涉水本义。",
    "鸣": "本关专属形象：头部裂开成一张巨口的鸟怪——对应「鸣」的鸟鸣本义。",
    "逐": "本关专属形象：低身冲锋的豕形怪——对应「逐」的追逐本义。",
    "安": "本关专属形象：屋形怪，屋脊为背、门洞为口——对应「安」的居所本义（宀＋女）。",
    "家": "本关专属形象：屋顶下立豕的怪物——对应「家」的字形（宀＋豕）。",
    "木": "本关专属形象：树身怪，枝为臂、根为足——对应「木」的字形。",
    "象": "本关专属形象：卷鼻高举的象怪——对应「象」的象形本义。",
    "龜": "本关专属形象：背甲隆起的巨龟——对应「龜」的象形本义。",
    "車": "本关专属形象：双轮战车化身的怪物——对应「車」的字形。",
}


def flatten(src, dst):
    im = Image.open(src).convert("L")
    a = np.asarray(im).astype(np.float32)
    # 纸底偏亮、线条偏暗；用一个中间阈值把"是不是线"分出来
    lo, hi = np.percentile(a, 12), np.percentile(a, 96)
    t = np.clip((a - lo) / max(1e-3, hi - lo), 0.0, 1.0)
    # t 越小越像墨线：反相后做软阈值，边缘不锯
    line = np.clip((0.62 - t) / 0.35, 0.0, 1.0)
    line = np.asarray(
        Image.fromarray((line * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.6))
    ).astype(np.float32) / 255.0
    rgb = np.zeros(a.shape + (3,), dtype=np.float32)
    for k in range(3):
        rgb[:, :, k] = FILL[k] * (1 - line) + INK[k] * line
    alpha = np.where(line > 0.06, 255, 0).astype(np.uint8)
    out = Image.fromarray(np.dstack([rgb.astype(np.uint8), alpha]), "RGBA")
    bb = out.split()[-1].getbbox()
    if bb:
        out = out.crop(bb)
    H = 500
    out = out.resize((max(1, round(out.width * H / out.height)), H), Image.LANCZOS)
    out.save(dst, "PNG", optimize=True)
    return out


def main():
    swap_path = "js/core/boss-art-swap.json"
    doc = json.loads(io.open(swap_path, encoding="utf-8").read())
    swap = doc["swap"]
    made = []
    for src, slug, ch, name in JOBS:
        s = "C:/DSH/comfy_assets/boss9/" + src
        if not os.path.exists(s):
            print("  缺 %s" % src)
            continue
        dst = "assets/boss/%s.png" % slug
        out = flatten(s, dst)
        swap[ch] = {
            "art": dst, "of": ch, "name": name, "tie": "专属",
            "why": WHY[ch],
        }
        made.append((ch, dst, out.size, os.path.getsize(dst) // 1024))
    io.open(swap_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print("  接入 %d 关：" % len(made))
    for ch, dst, size, kb in made:
        print("    %-3s %-26s %dx%d %4d KB" % (ch, dst, size[0], size[1], kb))
    print("  swap 现有 %d 条" % len(swap))


if __name__ == "__main__":
    main()
