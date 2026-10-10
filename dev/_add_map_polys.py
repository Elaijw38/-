# -*- coding: utf-8 -*-
"""给 levels.json 的区块加不规则多边形（拼图块），替换原来的网格 cell 定位。

四块四边形按「象限」无缝拼接，中央占卜坑是叠在中间的菱形：
    ┌──────────┬──────────┐
    │ 自然风光  │  动植物   │
    ├──────◇───┴───◇──────┤
    │ 单字练习  │ 生产生活  │
    └──────────┴──────────┘
顶点按边界对齐（如左半右边界 x=520 同时是右半的左边界），因此拼起来无缝隙——
这一点必须先算清楚，否则相邻块之间会露出底色，看着像地裂。
"""
import io, json, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "js", "core", "levels.json")
doc = json.loads(io.open(P, encoding="utf-8").read())
m = doc["map"]

# 画布 1000x720；中央菱形 400,360 / 520,200 / 640,360 / 520,520
POLY = {
    "landscape": {
        "poly": "0,0 520,0 520,200 400,360 520,520 520,720 0,720",
        "label": [215, 215],
        "note": "西北：山川日月所出"
    },
    "creature": {
        "poly": "520,0 1000,0 1000,720 520,720 520,520 640,360 520,200",
        "label": [810, 215],
        "note": "东北：林麓鸟兽所栖"
    },
    "practice": {
        "poly": "0,720 0,360 200,360 520,520 520,720",
        "label": [170, 590],
        "note": "西南：原样的单字选构练习"
    },
    "life": {
        "poly": "520,520 840,360 1000,360 1000,720",
        "label": [880, 590],
        "note": "东南：邑中聚居之处"
    },
    "center": {
        "poly": "400,360 520,200 640,360 520,520",
        "label": [520, 372],
        "note": "正中：灼骨问天之处"
    },
}

m["viewBox"] = "0 0 1000 720"
m.pop("cols", None)
m.pop("rows", None)

for z in m["zones"]:
    spec = POLY.get(z["id"])
    if not spec:
        print("!! 未定义多边形的区块:", z["id"])
        continue
    z.pop("cell", None)
    z["poly"] = spec["poly"]
    z["label"] = spec["label"]
    z["note"] = spec["note"]

io.open(P, "w", encoding="utf-8", newline="\n").write(
    json.dumps(doc, ensure_ascii=False, indent=2) + "\n")

print("已更新:", os.path.normpath(P))
for z in m["zones"]:
    print("  %-12s poly=%s" % (z["name"], z.get("poly", "(无)")[:44] + "…"))
