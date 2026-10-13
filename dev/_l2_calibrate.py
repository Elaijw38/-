# -*- coding: utf-8 -*-
"""第二关（殷商王邑）：**坐标与字表的唯一真源**，并按项目既有流程重建运行时数据。

## 为什么重做

`js/core/levels.json` 里 objects 的 x/y 原来是**旧版王邑底图** `assets/wangyi-map.jpg`
（1800×1010）的坐标；`assets/level2-0X-*.jpg` 与 `out/level2-maps/` 六张新图是
另一套 2624×1472 空间。上一轮的坐标写在新图空间里但只写进了 `_data.js`，
两份数据各说各话（levels.json 仍是旧坐标），这正是 HANDOFF「1.5 两套坐标空间」
记的那个坑的变体。

本轮统一成 **一套空间**：2624 × 1472，即六张图自己的像素空间。
大地图与小地图共用它，所以「热点落在哪」与「点击命中哪」永远是同一个换算。

## 数据来源与核对方式

- 字表：`out/level2-charset-audit.md` 盘点的 61 字（天象 4 · 山川 9 · 草木 6 ·
  禽兽虫鱼 9 · 人居器物 33），与现有 levels.json 字表逐字一致——**未增删任何字**。
- 坐标：在**最新六张图**上用 `dev/_l2_grid.py` 出带像素刻度的 3×3 放大块，
  逐字读出目标物中心；再用 `dev/_l2_overlay_new.py` 叠图复核（见 out/level2-maps/_calib）。
  **没有沿用旧图上测得的坐标**——world / life 两张图在上一轮位图后改过构图。
- 甲骨字形：一律取 `App.glyphs.parts`（73 字），不新造、不重画。
- `form`：构形说明（象形本义），由本脚本写入，措辞取通说。

## 输出

1. `js/core/levels.json`  —— map.zones[].objects 的 x/y/r/meaning/form，
   zone.art、map.worldImage、map.viewBox、map.artSpace
2. `js/core/_data.js`     —— 调 `dev/_build_leveldata.py` 重新打包（先备份）

用法：
  python dev/_l2_calibrate.py            # 写入并自检
  python dev/_l2_calibrate.py --dry      # 只打印差异，不写文件
"""
import io
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(REPO, "js", "core", "levels.json")
DATAJS = os.path.join(REPO, "js", "core", "_data.js")
PY = sys.executable

ART_SPACE = (2624, 1472)

# 五区：id -> (名称, 插画, 一句话说明)
ZONES = [
    ("sky",   "天象",     "assets/level2-01-sky.jpg",     "日月雨火：抬头看天"),
    ("land",  "山川",     "assets/level2-02-land.jpg",    "山丘谷石土泉川水田：脚下的地与水"),
    ("plant", "草木",     "assets/level2-03-plant.jpg",   "木林竹禾米屮：身边的草木"),
    ("beast", "禽兽虫鱼", "assets/level2-04-beast.jpg",   "豕鹿牛羊犬虎虫鱼隹：走动的生灵"),
    ("life",  "人居器物", "assets/level2-05-life.jpg",    "邑郭门屋、陶铜玉石、人的身体"),
]

WORLD_IMAGE = "assets/level2-world.jpg"

# ---------------------------------------------------------------
# 61 个字物：char -> (x, y, r, meaning, form)
#   坐标空间 2624×1472（分区插画自己的像素空间）
#   r：既是点击半径也是点亮范围；最小 58，保证手指可点（见 HANDOFF 移动端口径）
#   form：构形说明（象形本义，通说口径；不写争议性考释）
# ---------------------------------------------------------------
TABLE = {
    "sky": [
        ("日", 430, 300,  96, "一轮圆日",       "象日之形：一个圆，中间一点或一横，是太阳的轮廓。"),
        ("月", 2140, 330, 90, "一弯弦月",       "象月之形：一弯新月，中间一竖表示月面的暗影。"),
        ("雨", 1250, 570, 96, "云脚落下的雨丝", "象雨之形：上面一横是天，下面几点是落下的雨滴。"),
        ("火", 1380, 1150, 100, "升腾的火焰",   "象火之形：一簇上腾的火焰，两旁有火星。"),
    ],
    "land": [
        ("山", 400, 300,  96, "并列的峰峦",     "象山之势：三座并立的山峰，中峰最高。"),
        ("丘", 1250, 350, 92, "低缓的圆丘",     "象丘之形：比「山」低平的两座土丘。"),
        ("谷", 2300, 300, 88, "两坡之间的低谷", "从「水」从「口」：山口处两坡夹出的一道低地。"),
        ("石", 1000, 1200, 74, "河滩上的大石",  "从「厂」从「口」：山崖下一块石头。"),
        ("土", 1050, 900, 84, "隆起的一堆土",   "象土之形：地面上隆起的一堆土块。"),
        ("泉", 480, 750, 76, "石间涌出的水",    "象泉之形：石穴里涌出的水，细流不断。"),
        ("川", 2150, 830, 96, "宽阔的主河道",   "象川之形：两岸之间宽阔的水流，是与「水」相别的大水道。"),
        ("水", 1050, 1150, 66, "较窄的溪流",    "象水之形：中间一条主流，两旁几点水花。"),
        ("田", 2320, 1010, 92, "格状的田亩",    "象田之形：一块方田，中间纵横的田埂划出阡陌。"),
    ],
    "plant": [
        ("木", 420, 700,  92, "左侧的独立大树", "象木之形：上为枝、下为根、中为干。"),
        ("林", 930, 420,  92, "成片的树林",     "从二「木」：两棵树并立，表示成片的树林。"),
        ("竹", 2180, 640, 88, "丛生的竹子",     "象竹之形：两枝并生的竹竿，下垂的叶片。"),
        ("禾", 1420, 500, 92, "低垂的谷穗",     "象禾之形：一株成熟下垂的谷子。"),
        ("米", 1060, 1280, 76, "成堆的米粒",    "象米之形：谷粒散落的许多小点。"),
        ("屮", 1650, 1150, 72, "初生的小草",    "象草之形：一株刚出土的草，只有两片叶。"),
    ],
    "beast": [
        ("豕", 380, 1000, 92, "体肥耳大的家豕", "象豕之形：肥腹短足的家猪，长吻大耳。"),
        ("鹿", 560, 420,  92, "枝角分歧的鹿",   "象鹿之形：头上一对分枝的鹿角最醒目。"),
        ("牛", 1720, 400, 92, "双角横张的牛",   "象牛之形：正面牛头，一对角向上弯。"),
        ("羊", 2380, 460, 84, "角向下弯的羊",   "象羊之形：与「牛」同为头形，角向下卷曲。"),
        ("犬", 950, 1120, 88, "卷尾的犬",      "象犬之形：侧身的狗，长身卷尾。"),
        ("虎", 2100, 800, 96, "张口有纹的虎",   "象虎之形：巨口利爪，身上有斑纹。"),
        ("虫", 2020, 1230, 84, "蜷曲的蛇",      "象蛇之形：一条蜷曲的长虫，是「虫」的本形。"),
        ("鱼", 1120, 1150, 88, "水中的鱼",      "象鱼之形：一头一尾，身上有鳞纹。"),
        ("隹", 1130, 180, 72, "短尾的鸟",       "象鸟之形：短尾的鸟，「隹」与「鸟」本是一类。"),
    ],
    "life": [
        # 顺序与现有数据逐字一致（不得增删改序）：
        # 邑 郭 门 宀 囗 鼎 缶 皿 酉 玉 井 舟 卜 贝 糸 弓 矢 刀 斧 斤 戈 衣 大 力 人 目 耳 口 止 又 女 子 足
        ("邑", 1100, 600,  100, "环壕围绕的城邑", "从「囗」从「卩」：围起来的一块地方，人聚居之处。"),
        ("郭", 260, 950,  96, "城邑的外墙",      "从「邑」从「𩫏」：城邑外围的墙。"),
        ("门", 1180, 730, 84, "城邑的城门",      "象门之形：两扇对开的门板。"),
        ("宀", 560, 370,  84, "屋舍的屋顶",      "象屋顶之形：两面坡的屋顶，是房屋的初文。"),
        ("囗", 420, 620,  80, "围起来的地域",    "象围合之形：一圈边界，表示围起来的地方。"),
        ("鼎", 1100, 450, 84, "三足两耳的鼎",    "象鼎之形：上有耳、下有腹与三足。"),
        ("缶", 1230, 360, 88, "大腹小口的陶缶",  "象缶之形：小口大腹的瓦器。"),
        ("皿", 1620, 370, 84, "盛物的浅盘",      "象皿之形：浅而宽的盛器。"),
        ("酉", 1810, 600, 76, "窄口深腹的青铜酒器", "象酒器之形：窄口、大腹、尖底的盛酒器。"),
        ("玉", 1690, 760, 76, "串起来的玉环",    "象玉之形：一根绳上串起的几片玉。"),
        ("井", 380, 720,  76, "带木栏的水井",    "象井口之形：井栏交叉的木框。"),
        ("舟", 1960, 630, 92, "水边的木舟",      "象舟之形：中空的长方形船身，两边有船舷。"),
        ("卜", 1470, 640, 72, "灼出裂纹的龟甲",  "象卜之形：骨面上灼出的纵横裂纹，即兆。"),
        ("贝", 1600, 720, 72, "散落的海贝",      "象贝之形：两扇相合的海贝。"),
        ("糸", 1500, 600, 68, "一束丝",          "象丝之形：绞在一起的一束丝线。"),
        ("弓", 2140, 540, 76, "张开的弓",        "象弓之形：弯曲的弓身与弦。"),
        ("矢", 2180, 650, 72, "平放的直箭",      "象矢之形：一支箭，前为镞、后为羽。"),
        ("刀", 1380, 220, 72, "青铜小刀",        "象刀之形：刀身与短柄。"),
        ("斧", 1420, 250, 70, "横刃的斧",        "象斧之形：宽刃的劈砍工具。"),
        ("斤", 1300, 620, 68, "窄刃的斤",        "象斤之形：横刃的斧斤，用于削平木料。"),
        ("戈", 1520, 560, 70, "长柄横刃的戈",    "象戈之形：长柄横装的勾兵。"),
        ("衣", 1360, 990, 72, "祭祀者身上的衣",  "象衣之形：上衣的领与两袖。"),
        ("大", 960, 1000, 92, "正面张臂的大人",  "象大人之形：正面站立、双臂张开的人。"),
        ("力", 2480, 1300, 84, "翻土的耒耜",     "象耒之形：下端入土的尖头农具，用力翻土。"),
        ("人", 1120, 940, 84, "侧身站立的人",    "象人之形：侧身站立、垂手的人。"),
        ("目", 1030, 840, 62, "正面人物的眼睛",  "象目之形：一只横过来的眼睛，中有瞳。"),
        ("耳", 1530, 760, 62, "侧身人物的耳朵",  "象耳之形：耳朵的轮廓与耳孔。"),
        ("口", 1080, 900, 60, "正面人物的嘴",    "象口之形：张开的嘴，是「口」的本形。"),
        ("止", 1110, 1310, 62, "人的脚趾",       "象足趾之形：脚掌与三个脚趾。"),
        ("又", 1580, 880, 62, "人的右手",        "象右手之形：三指伸开的一只右手。"),
        ("女", 1080, 1200, 80, "跪坐的女子",     "象女子之形：跪坐、双手交叉于身前。"),
        ("子", 1540, 1160, 76, "小童",           "象小儿之形：头大、双臂上举的幼儿。"),
        ("足", 1250, 1350, 62, "人的脚",         "从「口」从「止」：连着小腿的整只脚。"),
    ],
}

# 大地图上五区入口（2624×1472）。选点原则：
#   落在**该主题可辨识的地貌**上，彼此拉开，不挤在一条线上；
#   低对比、不做成卡片（见需求「一、2」）。
#   天象 → 北部最高的雪顶山脉；山川 → 南部山脚的水源与河道交界；
#   草木 → 左侧最大的一片密林；禽兽虫鱼 → 右下水泽与飞鸟；
#   人居器物 → 城邑与田亩。
WORLD_PINS = {
    "sky":   (1700, 300,  340),
    "land":  (1250, 560,  320),
    "plant": (300, 1150,  340),
    "beast": (2200, 1160,  340),
    "life":  (1400, 1250,  320),
}


def build_objects(zid):
    out = []
    for ch, x, y, r, mean, form in TABLE[zid]:
        out.append({"char": ch, "x": int(x), "y": int(y), "r": int(r),
                    "meaning": mean, "form": form})
    return out


def main():
    dry = "--dry" in sys.argv
    zone_by_id = {z[0]: z for z in ZONES}

    doc = json.loads(io.open(LEVELS, encoding="utf-8").read())
    m = doc["map"]

    # 原有字表：逐区取出，用来核对「一个字不多、一个字不少、顺序一致」
    old_chars = {}
    for z in m["zones"]:
        old_chars[z["id"]] = [o["char"] for o in z["objects"]]

    print("=== 一、字表核对（不得增删改序）===")
    bad = 0
    for zid, name, art, note in ZONES:
        want = [r[0] for r in TABLE[zid]]
        have = old_chars.get(zid, [])
        same = (want == have)
        if not same:
            bad += 1
        print("  %-6s %-8s 新 %2d 字 · 原 %2d 字 · 逐字一致=%s"
              % (zid, name, len(want), len(have), "是" if same else "否 ← 不一致"))
        if not same:
            print("     原：%s" % " ".join(have))
            print("     新：%s" % " ".join(want))
    total = sum(len(r) for r in TABLE.values())
    print("  合计 %d 字（期望 4+9+6+9+33 = 61）" % total)
    if total != 61:
        raise SystemExit("!! 字数不是 61，拒绝写入")
    if bad:
        raise SystemExit("!! 有分区字表与现有数据不一致，拒绝写入（不要凭空改字表）")

    print("\n=== 二、坐标合法性 ===")
    for zid, name, art, note in ZONES:
        objs = build_objects(zid)
        oob = [o["char"] for o in objs
               if not (0 <= o["x"] <= ART_SPACE[0] and 0 <= o["y"] <= ART_SPACE[1])]
        # 重叠自检：两热点圆心距 < 两者半径和的 0.6 倍，算会互相抢点击
        near = []
        for i in range(len(objs)):
            for j in range(i + 1, len(objs)):
                a, b = objs[i], objs[j]
                d = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
                if d < (a["r"] + b["r"]) * 0.6:
                    near.append("%s/%s 距%.0f (r %d+%d)"
                                % (a["char"], b["char"], d, a["r"], b["r"]))
        print("  %-6s 越界 %d 个 · 抢点击 %d 对 %s"
              % (zid, len(oob), len(near), ("；".join(near) if near else "")))
        if oob:
            raise SystemExit("!! %s 有越界坐标：%s" % (zid, oob))

    print("\n=== 三、大地图入口点位 ===")
    for zid, name, art, note in ZONES:
        px, py, pr = WORLD_PINS[zid]
        print("  %-6s %-8s (%d, %d) 区域半径 %d" % (zid, name, px, py, pr))

    if dry:
        print("\n--dry：未写入任何文件。")
        return 0

    # ---------- 写入 levels.json ----------
    m["viewBox"] = "0 0 %d %d" % ART_SPACE
    m["worldImage"] = WORLD_IMAGE
    m["artSpace"] = "%d×%d" % ART_SPACE
    m["bgImage"] = WORLD_IMAGE
    m["bgCredit"] = ("大地图与五张分区插画：本项目原创学习示意图（Agnes AI 生成），"
                     "非考古复原，无第三方水印。")
    m["hint"] = "点大地图上的五个区域进入小地图；点实物认甲骨文。"
    m["intro"] = ("这是一座三千年前的王邑。五个区域可以任意顺序进入，"
                  "每认得一个实物，那一处就亮起来；一个区域学完，大地图上对应的那一片就点亮。")

    for z in m["zones"]:
        zid = z["id"]
        if zid not in zone_by_id:
            continue
        name, art, note = zone_by_id[zid][1], zone_by_id[zid][2], zone_by_id[zid][3]
        z["name"] = name
        z["art"] = art
        z["note"] = note
        z["objects"] = build_objects(zid)
        px, py, pr = WORLD_PINS[zid]
        z["world"] = {"x": px, "y": py, "r": pr}

    # 把五区的入口点也写进 objects 之外的一个只读引用，便于自检
    m["worldPins"] = {k: {"x": v[0], "y": v[1], "r": v[2]}
                      for k, v in WORLD_PINS.items()}

    io.open(LEVELS, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print("\n  已写 %s" % os.path.relpath(LEVELS, REPO))

    # ---------- 备份并重建 _data.js ----------
    bak = DATAJS + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(DATAJS, bak)
        print("  已备份 %s" % os.path.relpath(bak, REPO))
    r = subprocess.run([PY, os.path.join(REPO, "dev", "_build_leveldata.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    print("  " + (r.stdout or "").strip().replace("\n", "\n  "))
    if r.returncode != 0:
        raise SystemExit("!! _build_leveldata.py 失败：%s" % (r.stderr or "")[:400])

    # ---------- 复盘：从重建后的 _data.js 读回来核对 ----------
    t = io.open(DATAJS, encoding="utf-8").read()
    head = "App.levels = "
    i = t.index(head) + len(head)
    depth = 0
    for j in range(i, len(t)):
        if t[j] == "{":
            depth += 1
        elif t[j] == "}":
            depth -= 1
            if depth == 0:
                blob = t[i:j + 1]
                break
    rt = json.loads(blob)
    print("\n=== 四、重建后复盘（读 _data.js）===")
    n = 0
    for z in rt["map"]["zones"]:
        n += len(z["objects"])
        s = z["objects"][0]
        print("  %-6s %-8s %2d 字 · art=%s · 首字 %s(%d,%d,r%d)"
              % (z["id"], z["name"], len(z["objects"]), z["art"],
                 s["char"], s["x"], s["y"], s["r"]))
    print("  合计 %d 字 · viewBox=%s · world=%s"
          % (n, rt["map"]["viewBox"], rt["map"].get("worldImage")))
    print("  坐标齐全=%s"
          % all(("form" in o and "meaning" in o) for z in rt["map"]["zones"]
                for o in z["objects"]))
    if n != 61:
        raise SystemExit("!! 复盘字数不是 61")
    return 0


if __name__ == "__main__":
    sys.exit(main())
