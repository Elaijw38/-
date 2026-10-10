# -*- coding: utf-8 -*-
"""重建王邑实物地图：坐标重排 + 区块标题显式定位。

修的问题：上一版标题按「最上实物再上移」定位，而自然风光区最上的是
高处的日、月，于是标题被顶到地图中部，压住了牛、羊等实物。
现在标题位置直接写进数据（titleX/titleY），不再推导。

画布加高到 1240×960，三条带各留出标题行：
    0   ~ 150   山川草木 标题
    170 ~ 500   山川草木 实物
    530 ~ 570   禽兽虫鱼 标题
    590 ~ 860   禽兽虫鱼 实物
    960 之后    —— 这是错的，改为下面的实际布局
实际布局：
    标题一 y=150  → 实物 190~480
    标题二 y=530  → 实物 570~800
    标题三 y=850  → 实物 890~960（会被裁，故改用两列布局）
因此把「人居器物」的 33 个实物排成 4 行、每行 9 个，落在 870~1000 内，
画布高 1040。
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "js", "core", "levels.json")
OLD = os.path.join(os.environ["TEMP"], "old_levels.json")

MEAN = {
    "日": "一轮圆日，中加一点", "月": "一弯弦月，中有一竖", "雨": "云下有水点落下",
    "火": "火焰升腾之形",
    "山": "三峰并立", "水": "流水蜿蜒，两侧有滴", "川": "水道分流",
    "泉": "石穴中涌出的水", "谷": "两山之间的低地", "丘": "隆起的小土山",
    "土": "地面上的一堆土", "石": "山崖下的石块", "田": "阡陌纵横的田亩",
    "木": "树干枝叶分张", "林": "两木并立成林", "竹": "两片下垂的竹叶",
    "禾": "谷穗低垂", "米": "禾穗上散落的米粒", "屮": "初生的草",
    "牛": "牛头，双角横张", "羊": "羊头，双角下弯", "犬": "犬侧立，尾上卷",
    "豕": "猪，腹大尾垂", "鱼": "鱼形，有头有尾有鳍", "隹": "短尾鸟",
    "虎": "虎形，张口有纹", "鹿": "鹿，角枝分歧", "虫": "蛇形蜷曲",
    "宀": "房屋的屋顶", "门": "双扇的门", "邑": "城邑，人聚居之处",
    "郭": "外城墙", "囗": "方框，围起来的地域", "井": "井口的木栏", "舟": "船形",
    "鼎": "三足两耳之鼎", "缶": "大腹小口的陶器", "皿": "盛物的盘", "酉": "酒坛",
    "玉": "串起来的玉", "衣": "上衣", "弓": "弯曲的弓身", "矢": "箭，有镞有羽",
    "刀": "刀形", "斧": "斧头", "斤": "斧斤", "戈": "长柄横刃",
    "人": "侧立的人", "目": "眼睛", "耳": "耳朵", "口": "嘴", "止": "脚趾",
    "又": "右手", "女": "跪坐的女子", "子": "幼儿", "足": "脚",
    "力": "耒耜，翻土的农具", "大": "正面站立的大人",
    "卜": "龟甲上灼出的裂纹", "贝": "贝壳", "糸": "一束丝",
}


def row(chars, y, x0=110, step=118):
    return [(c, x0 + i * step, y) for i, c in enumerate(chars)]


# 山川草木：标题 y=110，实物 210~530
# 左两列放天象/山川/水泉，右两列（x>=620）放草木，避免左右撞在一起
NATURE = (
    row(list("日月雨火"), 210, x0=800, step=132)
    + [("山", 110, 330), ("丘", 228, 330), ("石", 346, 330), ("谷", 464, 330)]
    + [("土", 110, 450), ("泉", 228, 450), ("川", 346, 450), ("水", 464, 450),
       ("田", 110, 570)]
    + [("木", 620, 330), ("林", 738, 330)]
    + [("竹", 620, 450), ("禾", 738, 450)]
    + [("米", 620, 570), ("屮", 738, 570)]
)

# 禽兽虫鱼：标题 y=670，实物 770~1000（与上一区末行 570 隔 200，够开）
CREATURE = row(list("牛羊犬"), 770, x0=824, step=132) \
    + row(list("豕鱼隹"), 890, x0=824, step=132) \
    + row(list("虎鹿虫"), 1010, x0=824, step=132)

# 人居器物：标题 y=1140，实物 1240~1480，四行十列
LIFE = (row(list("宀门邑郭囗鼎缶皿酉玉"), 1240, x0=110, step=112)
        + row(list("井舟卜贝糸弓矢刀斧斤"), 1360, x0=110, step=112)
        + row(list("大力人目耳口止又女子"), 1480, x0=110, step=112)
        + row(list("足戈衣"), 1600, x0=110, step=112))

ZONES = [
    ("nature", "山川草木", "郊野所见：日月山川、林木禾稼", 100, 110, NATURE),
    ("creature", "禽兽虫鱼", "林麓水泽：牛羊犬豕、鹿虎鱼鸟", 824, 670, CREATURE),
    ("life", "人居器物", "邑中生计：屋舍井舟、鼎彝兵器", 110, 1140, LIFE),
]

old = json.loads(io.open(OLD, encoding="utf-8").read())

zones = []
for zid, zname, znote, tx, ty, pts in ZONES:
    zones.append({
        "id": zid,
        "name": zname,
        "note": znote,
        "titleX": tx, "titleY": ty,
        "objects": [
            {"char": ch, "x": x, "y": y, "meaning": MEAN.get(ch, "")}
            for ch, x, y in pts
        ],
    })

doc = {
    "_note": ("王邑实物地图：zones[].objects 是地图上的实物点"
              "（char=字, x/y=坐标, meaning=象形说明）；"
              "titleX/titleY 是区块标题位置。改这里即可增删实物，无需改代码。"),
    "_version": "3.0",
    "map": {
        "id": "wangyi-map",
        "name": "殷商王邑",
        "subtitle": "点击实物，认甲骨文",
        "intro": ("这是一张三千年前的王邑。图上每一样东西，都是一枚甲骨文——"
                  "点它，看古人怎么把它画成一个字。"),
        "viewBox": "0 0 1240 1700",
        "zones": zones,
        "quiz": {
            "note": "答题型玩法（拆字 / 配对 / 卜辞）的关卡数据，作为可选入口保留。",
            "zones": [
                {"id": z["id"], "name": z["name"], "mechanic": z.get("mechanic"),
                 "levels": z.get("levels", [])}
                for z in old["map"]["zones"] if z.get("levels")
            ],
        },
    },
}

io.open(P, "w", encoding="utf-8", newline="\n").write(
    json.dumps(doc, ensure_ascii=False, indent=2) + "\n")

# ---------- 自检 ----------
gl = json.loads(io.open(os.path.join(HERE, "..", "js", "core", "glyph-parts.json"),
                        encoding="utf-8").read())
parts = gl["parts"]
allpts, miss = [], []
for z in zones:
    for o in z["objects"]:
        if o["char"] not in parts:
            miss.append(o["char"])
        allpts.append((o["char"], o["x"], o["y"]))
chars = [p[0] for p in allpts]

print("区块 %d 个，实物 %d 个" % (len(zones), len(allpts)))
print("缺字形  : %s" % ("、".join(miss) if miss else "无 ✓"))
dups = sorted({c for c in chars if chars.count(c) > 1})
print("重复摆放: %s" % ("、".join(dups) if dups else "无 ✓"))
bad = []
for i in range(len(allpts)):
    for j in range(i + 1, len(allpts)):
        a, b = allpts[i], allpts[j]
        d = ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
        if d < 100:
            bad.append("%s(%d,%d)↔%s(%d,%d)=%.0f" % (a[0], a[1], a[2], b[0], b[1], b[2], d))
print("过近(<100): %s" % ("; ".join(bad) if bad else "无 ✓"))

# 标题不能压住任何实物（这才是本次要修的）
vw, vh = [int(v) for v in doc["map"]["viewBox"].split()[2:]]
clash = []
for z in zones:
    tx, ty = z["titleX"], z["titleY"]
    for o in z["objects"]:
        # 标题占位约 高 60、宽 = 字数*26
        if abs(o["y"] - ty) < 62 and (tx - 20) <= o["x"] <= (tx + len(z["name"]) * 28):
            clash.append("%s 标题压住 %s(%d,%d)" % (z["name"], o["char"], o["x"], o["y"]))
print("标题压字: %s" % ("; ".join(clash) if clash else "无 ✓"))
oob = [p for p in allpts if not (60 <= p[1] <= vw - 40 and 60 <= p[2] <= vh - 40)]
print("越出画布: %s" % ("、".join(p[0] for p in oob) if oob else "无 ✓"))
for z in zones:
    ys = [o["y"] for o in z["objects"]]
    print("  %-6s %2d 个，y 范围 %d~%d，标题 y=%d" % (
        z["name"], len(z["objects"]), min(ys), max(ys), z["titleY"]))
