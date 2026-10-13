# -*- coding: utf-8 -*-
"""把第二关六图的热点坐标与插画路径**一次性写进数据**，并接入页面。

本步负责三件事，全部自动完成，不再回头问：
  1. 六张图从 out/level2-maps/ 复制进 assets/（页面只引用 assets/）
  2. zones[].art 指向新的 assets 路径
  3. zones[].objects[].x/y 覆盖为复核后的坐标；并按物体的视觉大小补 r
     （原来 r 是"点亮范围"语义，这里同时用作点击半径）

坐标来源：dev/_build_hotspots.py 的清单 + out/_verify 叠图复核。
误差约 ±60~100px，热区半径按物体大小给 26~70。
"""
import io
import json
import os
import shutil

REPO = r"C:\DSH\字趣"
SRC = os.path.join(REPO, "out", "level2-maps")
ASSETS = os.path.join(REPO, "assets")

# 图 -> assets 文件名
ARTFILES = {
    "sky":   "level2-01-sky.jpg",
    "land":  "level2-02-land.jpg",
    "plant": "level2-03-plant.jpg",
    "beast": "level2-04-beast.jpg",
    "life":  "level2-05-life.jpg",
}
SRCMAP = {
    "sky":   "level2-01-sky-天象.jpg",
    "land":  "level2-02-land-山川.jpg",
    "plant": "level2-03-plant-草木.jpg",
    "beast": "level2-04-beast-禽兽虫鱼.jpg",
    "life":  "level2-05-life-人居器物.jpg",
}

# 复核后的坐标（x, y, r）。r 按物体视觉大小给，最小 26，前景区 46~70。
XY = {
    "sky": {
        "日": (250, 180, 70), "月": (2080, 190, 66),
        "雨": (1150, 300, 60), "火": (1100, 760, 56),
    },
    "land": {
        "山": (330, 300, 66), "丘": (1150, 350, 62), "谷": (1750, 620, 60),
        "石": (760, 1120, 46), "土": (1130, 880, 44), "泉": (430, 700, 40),
        "川": (1900, 620, 70), "水": (900, 1130, 40), "田": (2280, 960, 66),
    },
    "plant": {
        "木": (280, 700, 48), "林": (900, 300, 64), "竹": (2150, 300, 60),
        "禾": (1330, 500, 46), "米": (1010, 980, 34), "屮": (1690, 940, 34),
    },
    "beast": {
        "豕": (240, 990, 56), "鹿": (410, 350, 58), "牛": (1530, 280, 62),
        "羊": (2080, 400, 50), "犬": (940, 1080, 46), "虎": (1990, 810, 62),
        "虫": (1980, 1120, 46), "鱼": (1000, 900, 44), "隹": (1060, 190, 34),
    },
    "life": {
        # 城邑与建筑
        "邑": (900, 470, 70), "郭": (1120, 560, 60), "门": (930, 650, 40),
        "宀": (430, 330, 46), "囗": (250, 450, 46), "井": (500, 420, 40),
        # 器物与作坊
        "鼎": (2130, 400, 52), "缶": (1400, 200, 52), "皿": (1700, 240, 44),
        "酉": (1890, 230, 40), "玉": (2010, 480, 38), "舟": (2030, 790, 56),
        "卜": (2270, 660, 40), "贝": (1570, 540, 34), "糸": (1620, 590, 38),
        "弓": (2350, 540, 44), "矢": (2250, 590, 36), "刀": (1770, 380, 34),
        "斧": (1660, 420, 34), "斤": (1550, 340, 32), "戈": (1480, 500, 40),
        "衣": (1180, 1110, 40), "力": (2200, 1290, 52),
        # 人物
        "大": (1080, 1030, 60), "人": (1500, 1010, 56),
        "女": (1820, 1140, 52), "子": (1210, 1145, 34),
        # 身体部位（人物身上的小部位，半径按五官/肢体给，偏小是事实）
        # 目与口原来只差 46px，两热区叠在一起会点不准（自检报 46<56），这里拉开
        "目": (1055, 872, 30), "耳": (1495, 870, 30), "口": (1055, 950, 28),
        "止": (1230, 1355, 30), "又": (1330, 1015, 34), "足": (1500, 1335, 30),
    },
}


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


# 1) 复制图进 assets
print("  1) 复制六张图进 assets/")
for zid, dst in ARTFILES.items():
    s = os.path.join(SRC, SRCMAP[zid])
    if not os.path.exists(s):
        raise SystemExit("!! 缺图：%s" % s)
    shutil.copy2(s, os.path.join(ASSETS, dst))
    print("     %-22s %8d B" % (dst, os.path.getsize(os.path.join(ASSETS, dst))))

# 2+3) 写数据
print("\n  2) 写 art 路径与坐标")
for path, head in ((os.path.join(REPO, "js", "core", "levels.json"), None),
                   (os.path.join(REPO, "js", "core", "_data.js"), "App.levels = ")):
    if head is None:
        obj = json.load(io.open(path, encoding="utf-8"))
        raw = None
    else:
        t = io.open(path, encoding="utf-8").read()
        i = t.index(head) + len(head)
        a, b = span(t, t.index("{", i))
        obj = json.loads(t[a:b])
        raw = (t, a, b)

    ncoord = 0
    for z in obj["map"]["zones"]:
        zid = z["id"]
        if zid not in ARTFILES:
            continue
        z["art"] = "assets/" + ARTFILES[zid]
        for o in z["objects"]:
            v = XY[zid].get(o["char"])
            if not v:
                print("     !! %s 缺坐标：%s" % (zid, o["char"]))
                continue
            o["x"], o["y"], o["r"] = int(v[0]), int(v[1]), int(v[2])
            ncoord += 1

    if raw is None:
        io.open(path, "w", encoding="utf-8", newline="\n").write(
            json.dumps(obj, ensure_ascii=False, indent=1))
    else:
        t, a, b = raw
        out = t[:a] + json.dumps(obj, ensure_ascii=False,
                                 separators=(",", ":")) + t[b:]
        if len(out) < len(t) * 0.9:
            raise SystemExit("!! 新文件过小，拒绝写入")
        io.open(path, "w", encoding="utf-8", newline="\n").write(out)
    print("     %-18s art 5 个，坐标 %d 个" % (os.path.basename(path), ncoord))

# 自检
obj = json.load(io.open(os.path.join(REPO, "js", "core", "levels.json"), encoding="utf-8"))
tot = 0
print("\n  3) 自检")
for z in obj["map"]["zones"]:
    tot += len(z["objects"])
    ok = all(("x" in o and "y" in o and "r" in o) for o in z["objects"])
    print("     %-6s %-8s %2d 物件  坐标齐全=%s  art=%s"
          % (z["id"], z["name"], len(z["objects"]), "是" if ok else "否", z["art"]))
print("     合计 %d 物件" % tot)
