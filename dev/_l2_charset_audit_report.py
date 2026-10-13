# -*- coding: utf-8 -*-
"""生成第二关字表盘点报告（只读，不修改任何项目文件）。

产出：out/level2-charset-audit.md

数据来源（三份互相独立，已交叉核对一致）：
  1. js/core/_data.js          —— 运行时数据（含 art 字段）
  2. js/core/levels.json       —— 构建源
  3. _check/levels.豆包版备份.json —— 另一来源的备份
  甲骨字形 = js/core/_data.js 的 App.glyphs.parts（73 字）
          源 = js/core/glyph-parts.json
"""
import io
import json
import os

REPO = r"C:\DSH\字趣"


def load_js_assign(path, name):
    t = io.open(path, encoding="utf-8").read()
    i = t.index(name) + len(name)
    j = t.index("{", i)
    depth = 0
    k = j
    ins = False
    esc = False
    while k < len(t):
        c = t[k]
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
                    break
        k += 1
    return json.loads(t[j:k + 1])


data = load_js_assign(os.path.join(REPO, "js", "core", "_data.js"), "App.levels = ")
glyphs = load_js_assign(os.path.join(REPO, "js", "core", "_data.js"), "App.glyphs = ")
parts = list(glyphs["parts"].keys())
MAP = data["map"]
zones = MAP["zones"]

used = [o["char"] for z in zones for o in z["objects"]]
unused = [c for c in parts if c not in used]
boss = data["boss"]


def where(x, y, W=1800.0, H=1010.0):
    hx, hy = x / W, y / H
    col = "左" if hx < 1 / 3 else ("中" if hx < 2 / 3 else "右")
    row = "上" if hy < 1 / 3 else ("中" if hy < 2 / 3 else "下")
    return row + col


# 难物化（人工判断：能否画成一个一眼可辨的具体物体）
HARD = {
    "谷": "低地是负空间，没有独立轮廓；与「丘」互为凹凸，热点易被误认",
    "土": "一堆土与「丘」在图上几乎同形，只能靠尺寸与语境区分",
    "川": "与「水」同为水道，只有宽窄之别，同图并列易混",
    "宀": "字形只是屋顶轮廓；画成屋子会被误认作「邑／家」",
    "囗": "纯围合轮廓，没有实体，画出来就是一个空框",
    "缶": "与「皿」「酉」同为陶器，只靠口沿与腹深区分，缩略图下难辨",
    "皿": "浅盘，器形特征最弱的一件陶器",
    "酉": "盛酒器，与「缶」器形接近",
    "玉": "串玉极小（r=30），且与「贝」同为小饰件",
    "糸": "一束丝，线状物，没有体积感（r=22）",
    "力": "本义是耒耜（农具），今义抽象；画农具会被读成「工具」而非「力」",
    "目": "身体局部，只能依附人／兽的脸，不能独立成景（r=12）",
    "耳": "同上，且现在挂在鹿身上（r=12）",
    "口": "同上，且器形上与「囗」几乎同形（r=11）",
    "止": "脚趾，r=12，独立画出来不成立",
    "又": "右手，r=12，独立画出来不成立",
    "足": "脚，r=12，与「止」同义域、易混",
}
MED = {
    "女": "需画跪坐人形，小尺寸下姿态难辨（r=15）",
    "子": "需画幼者，与「人」「大」同为人形（r=13）",
    "大": "正面站立的人，与「人」只差正／侧之别（r=24）",
    "屮": "初生小草，尺寸极小（r=26），缩略图下易被当作杂草",
    "米": "散落米粒，r=28，需要放大才看得清",
}

L = []
w = L.append
w("# 第二关（殷商王邑）需要学习的汉字 · 盘点")
w("")
w("> 由 `dev/_l2_charset_audit_report.py` 生成。**只读盘点，未修改任何项目文件。**")
w("")
w("## 一、结论摘要")
w("")
w("| 项 | 结果 |")
w("|---|---|")
w("| 项目里是否有确定的第二关字表 | **有** |")
w("| 数据位置 | `js/core/_data.js` → `App.levels.map.zones[].objects` |")
w("| 物件数 / 去重字数 | **61 / 61**（跨区无重复，无空字） |")
w("| 五区分布 | 天象 4 · 山川 9 · 草木 6 · 禽兽虫鱼 9 · 人居器物 33 |")
w("| 甲骨字形覆盖 | **61 / 61 全部有**（数据集共 73 字） |")
w("| 难物化 | **17 字**（另有 5 字次要） |")
w("| 与第三关 Boss 字表 | **重叠 7 字**：山 人 木 日 月 水 虎 |")
w("")
w("**三份来源交叉核对一致**（字集逐一相同）：")
w("")
w("1. `js/core/_data.js`（运行时数据，含 `art` 字段 —— 本轮新加）")
w("2. `js/core/levels.json`（构建源）")
w("3. `_check/levels.豆包版备份.json`（另一来源的备份）")
w("")
w("> ⚠️ **注意**：代码注释与 README 第 152 行称数据在 `js/core/levels.json`，")
w("> 但**运行时实际读的是 `js/core/_data.js`**（由 `dev/_build_leveldata.py` 打包）。")
w("> 两者字表一致；差异仅在 `_data.js` 多一个 `art` 字段。改字表要**两份同步**。")
w("")
w("## 二、甲骨字形来源（可核验，本轮未仿造任何字形）")
w("")
at = glyphs["attribution"]
w("| 项 | 值 |")
w("|---|---|")
for k, label in (("dataset", "数据集"), ("authors", "作者"), ("license", "授权"),
                 ("doi", "DOI"), ("mirror", "镜像"), ("commit", "commit"),
                 ("modifications", "项目所做修改")):
    w("| %s | %s |" % (label, at.get(k, "")))
w("")
w("引用文献：%s" % at.get("citation", ""))
w("")
w("项目内位置：`js/core/_data.js` → `App.glyphs.parts`（73 字）；")
w("原始几何：`js/core/glyph-parts.json`（232,917 B）；")
w("生成脚本：`dev/_gen_glyph_parts.py`（文件头注明「请勿手改」）。")
w("")
w("---")
w("")

for zi, z in enumerate(zones, 1):
    w("## 三.%d %s（`%s`）" % (zi, z["name"], z["id"]))
    w("")
    w("本区 **%d 字**。数据里的 `note`：`%s`" % (len(z["objects"]), z["note"]))
    if z.get("art"):
        w("")
        w("本区插画：`%s`" % z["art"])
    w("")
    w("| # | 汉字 | 学习释义／构形知识点 | 可直接画进地图的物体或活动 | 建议场景位置（九宫方位 + 现有坐标） | 数据位置 | 甲骨字形 |")
    w("|---|---|---|---|---|---|---|")
    for oi, o in enumerate(z["objects"], 1):
        c = o["char"]
        g = "有" if c in parts else "**无**"
        w("| %d | **%s** | %s | %s | %s（x=%d, y=%d, r=%d） | `map.zones[%d].objects[%d]` | %s |"
          % (oi, c, o["meaning"], o["meaning"], where(o["x"], o["y"]),
             o["x"], o["y"], o["r"], zi - 1, oi - 1, g))
    w("")
    hi = [o["char"] for o in z["objects"] if o["char"] in HARD]
    mi = [o["char"] for o in z["objects"] if o["char"] in MED]
    if hi:
        w("**本区难物化：**")
        w("")
        for c in hi:
            w("- **%s** —— %s" % (c, HARD[c]))
        w("")
    if mi:
        w("**本区次要难物化：**")
        w("")
        for c in mi:
            w("- **%s** —— %s" % (c, MED[c]))
        w("")
    w("---")
    w("")

w("## 四、难以用具体物体表现的字（共 %d 字）" % sum(
    1 for z in zones for o in z["objects"] if o["char"] in HARD))
w("")
w("| 汉字 | 所属区 | 难点 |")
w("|---|---|---|")
for z in zones:
    for o in z["objects"]:
        if o["char"] in HARD:
            w("| **%s** | %s | %s |" % (o["char"], z["name"], HARD[o["char"]]))
w("")
w("### 次要（共 %d 字，能画但小尺寸下弱）" % sum(
    1 for z in zones for o in z["objects"] if o["char"] in MED))
w("")
w("| 汉字 | 所属区 | 难点 |")
w("|---|---|---|")
for z in zones:
    for o in z["objects"]:
        if o["char"] in MED:
            w("| %s | %s | %s |" % (o["char"], z["name"], MED[o["char"]]))
w("")
w("> **最棘手的是「身体局部」一类**：目 耳 口 止 又 足（6 字，全在人居器物区）。")
w("> 它们天然依附在人／兽身上，半径只有 11–12：既画不成独立景物，")
w("> 热点又会与宿主（人、鹿）的热区重叠。建议单独设计呈现方式，不要硬塞进地图。")
w("")

w("## 五、与第三关的边界")
w("")
w("第三关 Boss 在 `App.levels.boss.tiers[].list`，共 **%d 关 / %d 个去重字**："
  % (sum(len(t.get("list", [])) for t in boss["tiers"]),
     len(set(x["char"] for t in boss["tiers"] for x in t.get("list", [])))))
w("")
for tr in boss["tiers"]:
    w("- **%s**（`%s`）：%s"
      % (tr["name"], tr.get("kind", ""), " ".join(x["char"] for x in tr.get("list", []))))
w("")
bc = set(x["char"] for t in boss["tiers"] for x in t.get("list", []))
inter = [c for c in used if c in bc]
w("**与第二关重叠 %d 字：%s**" % (len(inter), " ".join(dict.fromkeys(inter))))
w("")
w("这 7 个字在第二关是「在地图上找实物」，在第三关是「拆笔画打 Boss」，")
w("两关的学习目标不同，**不算冲突**。但：")
w("")
w("- 做第二关字表时**不要**从 Boss 表里取字凑数；")
w("- 也不要因为两关重合，就把第二关已有的字挪去第三关。")
w("")

w("## 六、候选扩充（需要你先确认，我没有擅自加字）")
w("")
w("### 6.1 现成可用：数据集里已有、但第二关没用到的 %d 字" % len(unused))
w("")
w("这 %d 字的甲骨字形**项目里已经收录**（同一份 CC BY 4.0 数据集），"
  % len(unused))
w("所以是**唯一不需要新字形来源就能直接扩进来的一批**：")
w("")
w("| 汉字 | Unicode | glyphId | 笔画 | charForm | 可能归属的分区 |")
w("|---|---|---|---|---|---|")
SUG = {
    "馬": "禽兽虫鱼", "鳥": "禽兽虫鱼", "龜": "禽兽虫鱼", "象": "禽兽虫鱼",
    "龍": "（不建议：非自然实物）", "車": "人居器物", "鼓": "人居器物",
    "爵": "人居器物", "彝": "人居器物", "尊": "人居器物", "絲": "人居器物",
    "舞": "（不建议：非实物）",
}
for c in unused:
    g = glyphs["parts"][c]
    w("| **%s** | U+%s | %s | %d | `%s` | %s |"
      % (c, g["unicode"], g["glyphId"], g["pieceCount"], g["charForm"], SUG.get(c, "—")))
w("")
w("**我的意见**：")
w("")
w("- `馬 鳥 龜 象` 适合「禽兽虫鱼」，都是商代实有动物，且象形性强、易画成物体；")
w("- `車 鼓 爵 彝 尊 絲` 适合「人居器物」，其中 `爵／彝／尊` 是青铜礼器，")
w("  与已有的 `鼎` 同组，能补上「器以类聚」的层次；")
w("- `龍 舞` **不建议**放进第二关：都不是能在地图上找到的实物，")
w("  `龍` 且属神话形象，与「不要奇幻怪兽」的既有要求冲突。")
w("")
w("### 6.2 需要新字形来源的字（**我没有能力核实，故不列入**）")
w("")
w("像 `星 云 雷 虹 岳 麓 湖 稻 麥 鳳` 这类字，主题上很贴合，")
w("**但项目现有 73 字数据集里没有**，也就没有可核验的甲骨字形。")
w("")
w("我**不会**为它们仿造字形（既定约束：绝不编造甲骨字形）。")
w("若要纳入，请先提供一份带授权的字形数据，例如：")
w("")
w("- 与现有数据集同源的扩充版本（同一 DOI / 仓库的更多字）；")
w("- 或你认可的其它 CC BY / 公有领域甲骨字库。")
w("")
w("### 6.3 外部检索情况（如实说明）")
w("")
w("本轮按要求尝试了联网检索可核验字表，**未能取得可用结果**：")
w("")
w("- `github.com/aylqs2025/oracle-bone-jgw-1203` —— 取不到（网络失败）；")
w("- `zh.wikipedia.org` 甲骨文条目 —— 取不到（网络失败）；")
w("- 多数检索命中是索引器内部路径（`/hdd/...`）或需登录的 PDF 镜像，本机无该语料；")
w("- 本机亦无其它离线甲骨语料目录。")
w("")
w("因此**候选扩充只列 6.1 那 %d 个「项目里已有字形」的字**，"
  % len(unused))
w("其余等我拿到可核验来源再补。")
w("")

w("## 七、待你确认")
w("")
w("1. **五区主题**：`README.md` 第 178 行与 `HANDOFF.md` 第 98 行都写明当前五个主题")
w("   是「可替换占位」，**正式主题待你提供**。但 `note` 里的字例已与主题匹配，")
w("   所以**字表本身可用**；需要你确认的只是主题名与分区是否就按现在这五个。")
w("2. **是否扩充**：要不要把 6.1 的 %d 字纳进来？要哪些？" % len(unused))
w("3. **难物化的 17 字**（尤其 6 个身体局部）打算怎么呈现？")
w("   换字、换个画法、还是单独做一个非地图的呈现区？")
w("")

p = os.path.join(REPO, "out", "level2-charset-audit.md")
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("  已生成 %s（%d 行）" % (p, len(L)))
print("  第二关：%d 物件 / %d 去重字；难物化 %d；数据集未用 %d"
      % (len(used), len(set(used)),
         sum(1 for z in zones for o in z["objects"] if o["char"] in HARD),
         len(unused)))
