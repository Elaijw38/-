# -*- coding: utf-8 -*-
"""把 BOSS 战的内容写进 levels.json（内容与代码分离，和 map 一样）。

三档，对应设计的三个阶段：
  一阶 合体字 —— 身体＝构件拼成，拆掉构件即破（止=封走位、口=封印技能、水/火=消属性）
  二阶 独体字 —— 一段身体，几笔就散
  终极 繁复字 —— 构件拆分模糊的图画型古字，只能用笔画斩（車17段、虎17段…）
"""
import io, json, os

REPO = r"C:\DSH\字趣"
J = os.path.join(REPO, "js", "core", "levels.json")
GL = json.loads(io.open(os.path.join(REPO, "js", "core", "glyph-parts.json"), encoding="utf-8").read())
parts = GL["parts"]


def nseg(ch):
    return parts.get(ch, {}).get("pieceCount", 0)


# 构件 → 击破效果（设计稿：止封走位 / 口封印技能 / 水消水属性 / 火消火属性）
COMPOUND = [
    ("涉", ["水", "止"], "趟水过河——水与止缺一不可"),
    ("鸣", ["口", "隹"], "鸟鸣于口——口是它的喉咙"),
    ("焚", ["木", "火"], "以火烧林——木与火相生相杀"),
    ("逐", ["止", "豕"], "追豕而猎——止是它的腿"),
    ("安", ["宀", "女"], "室中有女则安——宀是它的屋顶"),
    ("家", ["宀", "豕"], "屋下养豕——拆了屋顶便不成家"),
]
SOLO = [("山", "三峰并立"), ("人", "侧立之人"), ("木", "树干枝叶"),
        ("日", "一轮圆日"), ("月", "一弯弦月"), ("水", "流水蜿蜒")]
ELITE = [("象", "长鼻巨兽"), ("龍", "鳞虫之长"), ("鳥", "短尾之鸟"),
         ("鼓", "以手击鼓"), ("馬", "长鬃之马"), ("龜", "甲虫之龟"),
         ("舞", "执牛尾而舞"), ("車", "双轮之车"), ("虎", "张口有纹之虎")]


def mk(ch, note, kind, comps=None):
    return {"char": ch, "note": note, "kind": kind,
            "comps": comps or [], "seg": nseg(ch)}


tiers = [
    {"id": "grunt", "name": "一阶 · 合体字", "kind": "compound",
     "note": "身体由构件拼成。拆掉构件就破——止封走位、口封印技能、水火消属性。",
     "list": [mk(c, n, "compound", cs) for c, cs, n in COMPOUND]},
    {"id": "solo", "name": "二阶 · 独体字", "kind": "stroke",
     "note": "独体象形，身上没有可拆的构件。直接拆它的笔画，几笔就散。",
     "list": [mk(c, n, "stroke") for c, n in SOLO]},
    {"id": "elite", "name": "终极 · 繁复字", "kind": "stroke",
     "note": "构件混同、拆分模糊的图画型古字。硬拆构件无效——只能用笔画斩，"
             "一段一段断它的纹路护甲。",
     "list": [mk(c, n, "stroke") for c, n in ELITE]},
]

d = json.loads(io.open(J, encoding="utf-8").read())
d["boss"] = {"_version": "1.0", "tiers": tiers}
io.open(J, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))

print("已写入 levels.json 的 boss 段：")
for t in tiers:
    print("  %-14s %d 个   %s" % (t["name"], len(t["list"]), t["note"][:34]))
    for b in t["list"]:
        extra = ("  构件=" + "+".join(b["comps"])) if b["comps"] else ("  笔画=%d 段" % b["seg"])
        print("      %-3s%s" % (b["char"], extra))
tot = sum(len(t["list"]) for t in tiers)
print("  合计 %d 个 BOSS" % tot)
missing = [b["char"] for t in tiers for b in t["list"] if b["char"] not in parts]
print("  缺字形: %s" % ("、".join(missing) if missing else "无 ✓"))
