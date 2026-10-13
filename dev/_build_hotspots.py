# -*- coding: utf-8 -*-
"""生成六张第二关地图的「学习对象位置清单」（初版）。

坐标怎么来的、可信到什么程度 —— 必须说清楚：
  · 依据：out/_grid/ 里的 200px 刻度网格图，逐项读出
  · 坐标系：图片像素，原点左上，范围 2624×1472
  · **误差约 ±60~100px**：我是看图读的，不是逐像素量的。
    对"把热点对准实物"来说，热区半径通常 40~60px，
    所以这份清单**够用但必须复核**。精确值请用 dev/_pick_hotspots.py 点一遍。

产出：
  out/level2-maps/hotspots.json          六张图的 {char,x,y} 清单
  out/level2-maps/hotspots.md            可读版
用法：
  python dev/_build_hotspots.py           重新生成清单文件
  python dev/_build_hotspots.py --apply   把清单写进 js/core/levels.json 与 _data.js
"""
import io
import json
import os
import sys

REPO = r"C:\DSH\字趣"
OUT = os.path.join(REPO, "out", "level2-maps")

# char -> (x, y, 一句定位说明)
H = {}

H["01-sky"] = {
    "日": (250, 190, "左上大圆日"),
    "月": (2120, 200, "右上弦月"),
    "雨": (1150, 330, "顶部云的雨丝"),
    "火": (1100, 790, "中央火焰"),
}
H["02-land"] = {
    "山": (330, 260, "左侧尖峰群"),
    "丘": (1130, 330, "中景浑圆低丘"),
    "谷": (1900, 470, "两坡之间的低谷"),
    "石": (600, 1230, "前景砾石滩上的大石"),
    "土": (1140, 760, "孤立的小土堆"),
    "泉": (740, 850, "两岩之间的泉眼与水池"),
    "川": (1500, 620, "中景最宽的主河道"),
    "水": (1180, 1080, "前景较窄的溪流"),
    "田": (1960, 1150, "右下格状田亩"),
}
H["03-plant"] = {
    "木": (340, 640, "左侧独立大树"),
    "林": (880, 330, "左中大片树林"),
    "竹": (2180, 430, "右侧竹丛"),
    "禾": (1500, 800, "中部结穗的禾"),
    "米": (1010, 1010, "散在地面的米粒堆"),
    "屮": (1830, 970, "右下初生小草丛"),
}
H["04-beast"] = {
    "豕": (250, 1050, "左下家豕"),
    "鹿": (350, 430, "左上大树下的大鹿"),
    "牛": (1600, 300, "右上最大的牛"),
    "羊": (2150, 420, "牛右侧的羊"),
    "犬": (900, 1180, "下方卷尾犬"),
    "虎": (2050, 780, "右侧斑纹虎"),
    "虫": (1900, 1130, "右下蜷曲的蛇"),
    "鱼": (1080, 900, "中央浅水中的两条鲤鱼"),
    "隹": (1080, 200, "上方短尾鸟"),
}
H["05-life"] = {
    # 城邑与建筑
    "邑": (600, 560, "整个城邑（外郭+房舍的整体）"),
    "郭": (330, 760, "左侧环绕的外墙"),
    "门": (900, 720, "城墙上的门楼"),
    "宀": (500, 300, "单独可辨的房顶轮廓"),
    "囗": (180, 500, "城旁独立围合的小院"),
    "井": (500, 430, "城内石砌水井"),
    # 器物与作坊
    "鼎": (2050, 430, "三足青铜鼎"),
    "缶": (1420, 260, "大腹小口陶缶"),
    "皿": (1650, 300, "浅而宽的陶皿"),
    "酉": (1900, 290, "窄口青铜酒器"),
    "玉": (1900, 495, "成堆的玉环"),
    "舟": (2020, 800, "水边木舟"),
    "卜": (2280, 620, "带灼裂纹的龟甲"),
    "贝": (1600, 530, "散落的海贝"),
    "糸": (1620, 610, "挂在本桩上的丝束"),
    "弓": (2350, 540, "立着的弯弓"),
    "矢": (2260, 590, "平放的直箭"),
    "刀": (1420, 380, "青铜小刀"),
    "斧": (1350, 420, "宽刃斧"),
    "斤": (1300, 350, "窄直角刃斤"),
    "戈": (1500, 470, "长柄横刃戈"),
    "衣": (1120, 1030, "大人物腰间衣物"),
    "力": (2200, 1290, "弯腰翻土处（耒耜）"),
    # 人物
    "大": (1080, 1080, "正面张臂的大人"),
    "人": (1480, 1050, "侧身站立的人"),
    "女": (1800, 1180, "跪坐的女子"),
    "子": (1200, 1150, "小童"),
    # 身体部位（人物身上的小部位，热点偏小）
    "目": (1050, 945, "正面人物的眼睛"),
    "耳": (1470, 905, "侧身人物的耳朵"),
    "口": (1045, 965, "正面人物的嘴"),
    "止": (1230, 1370, "正面人物的脚趾"),
    "又": (900, 1090, "正面人物张开的右手"),
    "足": (1470, 1360, "侧身人物的脚"),
}
H["00-world"] = {}

# ---------------------------------------------------------------- 修正表
# 第一版靠肉眼读网格，画回图上自查后发现近一半偏移。
# 这里按"标记必须落在实物中心"逐个校正（依据 out/_verify 的叠图）。
FIX = {
    "01-sky": {"日": (250, 180), "月": (2080, 190), "雨": (1150, 300), "火": (1100, 760)},
    "02-land": {"山": (330, 300), "丘": (1150, 350), "谷": (1750, 620),
                "石": (760, 1120), "土": (1130, 880), "泉": (430, 700),
                "川": (1900, 620), "水": (900, 1130), "田": (2280, 960)},
    "03-plant": {"木": (280, 700), "林": (900, 300), "竹": (2150, 300),
                 "禾": (1330, 500), "米": (1010, 980), "屮": (1690, 940)},
    "04-beast": {"豕": (240, 990), "鹿": (410, 350), "牛": (1530, 280),
                 "羊": (2080, 400), "犬": (940, 1080), "虎": (1990, 810),
                 "虫": (1980, 1120), "鱼": (1000, 900), "隹": (1060, 190)},
    "05-life": {
        "邑": (900, 470), "郭": (400, 730), "门": (930, 650), "宀": (430, 330),
        "囗": (250, 450), "井": (500, 420),
        "鼎": (2110, 380), "缶": (1400, 200), "皿": (1170, 250),
        "酉": (1160, 210), "玉": (2020, 490), "舟": (2050, 790),
        "卜": (2100, 500), "贝": (1720, 490), "糸": (1600, 550),
        "弓": (1950, 470), "矢": (1880, 520), "刀": (1770, 390),
        "斧": (1660, 430), "斤": (1560, 350), "戈": (1500, 520),
        "衣": (1180, 1120), "力": (2180, 1270),
        "大": (1080, 1050), "人": (1500, 1020), "女": (1820, 1140),
        "子": (1180, 1140),
        "目": (1050, 900), "耳": (1490, 880), "口": (1050, 950),
        "止": (1230, 1360), "又": (1300, 1030), "足": (1500, 1340),
    },
}

for _k, _d in FIX.items():
    for _c, (_x, _y) in _d.items():
        if _c in H[_k]:
            old = H[_k][_c]
            H[_k][_c] = (_x, _y, old[2])


def build():
    man = ["# 第二关六图 · 学习对象位置清单（初版）", ""]
    man.append("> 坐标系：图片像素，原点左上，范围 **2624×1472**。")
    man.append("> 依据 `out/_grid/` 的 200px 刻度网格逐项读出。")
    man.append("> **误差约 ±60~100px**，够用但必须复核；精确值请用 `dev/_pick_hotspots.py` 点一遍。")
    man.append("")
    total = 0
    for key in ("01-sky", "02-land", "03-plant", "04-beast", "05-life"):
        items = H[key]
        man.append("## %s（%d 项）" % (key, len(items)))
        man.append("")
        man.append("| 汉字 | x | y | 位置说明 |")
        man.append("|---|---|---|---|")
        for c, (x, y, note) in items.items():
            man.append("| **%s** | %d | %d | %s |" % (c, x, y, note))
        man.append("")
        total += len(items)
    man.append("**合计 %d 项**（天象 4 · 山川 9 · 草木 6 · 禽兽虫鱼 9 · 人居器物 33）" % total)
    man.append("")

    data = {k: [{"char": c, "x": v[0], "y": v[1], "note": v[2]}
                for c, v in items.items()] for k, items in H.items()}

    io.open(os.path.join(OUT, "hotspots.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(data, ensure_ascii=False, indent=1))
    io.open(os.path.join(OUT, "hotspots.md"), "w", encoding="utf-8",
            newline="\n").write("\n".join(man))
    print("  已生成 out/level2-maps/hotspots.json 与 hotspots.md")
    print("  合计 %d 项" % total)
    for k in ("01-sky", "02-land", "03-plant", "04-beast", "05-life"):
        print("    %-10s %d 项" % (k, len(H[k])))
    return data


def apply_to_data(data):
    """把清单写进 levels.json 与 _data.js（保留原有 meaning，只覆盖坐标）。"""
    def span(text, start):
        depth = 0
        i = start
        ins = esc = False
        while i < len(text):
            c = text[i]
            if ins:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    ins = False
            else:
                if c == '"':
                    ins = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return start, i + 1
            i += 1
        raise SystemExit("brace mismatch")

    KEYMAP = {"01-sky": "sky", "02-land": "land", "03-plant": "plant",
              "04-beast": "beast", "05-life": "life"}
    for path, head in ((os.path.join(REPO, "js", "core", "levels.json"), None),
                       (os.path.join(REPO, "js", "core", "_data.js"), "App.levels = ")):
        if head is None:
            data_obj = json.load(io.open(path, encoding="utf-8"))
            raw = None
        else:
            t = io.open(path, encoding="utf-8").read()
            i = t.index(head) + len(head)
            a, b = span(t, t.index("{", i))
            data_obj = json.loads(t[a:b])
            raw = (t, a, b)
        n = 0
        for z in data_obj["map"]["zones"]:
            key = [k for k, v in KEYMAP.items() if v == z["id"]]
            if not key:
                continue
            bychar = {o["char"]: o for o in data_obj and H[key[0]] or []}
            for o in z["objects"]:
                h = H[key[0]].get(o["char"])
                if h:
                    o["x"], o["y"] = int(h[0]), int(h[1])
                    n += 1
        if raw is None:
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                json.dumps(data_obj, ensure_ascii=False, indent=1))
        else:
            t, a, b = raw
            out = t[:a] + json.dumps(data_obj, ensure_ascii=False,
                                     separators=(",", ":")) + t[b:]
            if len(out) < len(t) * 0.9:
                raise SystemExit("!! 新文件过小，拒绝写入 %s" % path)
            io.open(path, "w", encoding="utf-8", newline="\n").write(out)
        print("  已写入 %s（%d 个坐标）" % (os.path.basename(path), n))


if __name__ == "__main__":
    d = build()
    if "--apply" in sys.argv:
        print()
        apply_to_data(d)
