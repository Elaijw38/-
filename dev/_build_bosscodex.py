# -*- coding: utf-8 -*-
"""把「讨伐名录」（Boss 形象字表）并进 js/core/levels.json 的 bossCodex 段。

数据来源分三处，各管一件事：
  js/core/boss-codex.json   《Boss（象形会意假借）.docx》的逐字转录（形象/部件/玩法）
  js/core/glyph-parts.json  甲骨字库（73 字）——决定这个字能不能真打成关卡
  assets/boss/*.png         形象资产（文件名即编号+拼音，本脚本按同一次序号推导）

产出既给「图鉴」用（形象/部件/玩法），也给作战界面用（按字取形象，回退到按档）。

可打性（playable）的判定：
  stroke    字库里就有整字甲骨形 → 直接斩笔画，机制现成
  compound  字库有它的构件 → 可以拼出身体、拆构件
  null      两者都没有。**不臆造字形**（全站硬规矩），只能作为名录存在

用法：python dev/_build_bosscodex.py
      再跑 python dev/_build_leveldata.py 把结果内联进 _data.js
"""
import io, json, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))

CODEX = os.path.join(REPO, "js", "core", "boss-codex.json")
LEVELS = os.path.join(REPO, "js", "core", "levels.json")
GLYPHS = os.path.join(REPO, "js", "core", "glyph-parts.json")
ARTDIR = os.path.join(REPO, "assets", "boss")

# 简繁互认：docx 用繁体写「龜魚貝門」，字库里有的是简体。只做等价替换，不改字。
ALIAS = {
    "魚": "鱼", "貝": "贝", "門": "门", "风": "風", "云": "雲", "凤": "鳳",
    "东": "東", "来": "來", "无": "無", "万": "萬", "旧": "舊", "见": "見",
    "罗": "羅", "获": "獲", "鸣": "鳴", "众": "眾", "网": "網", "龙": "龍",
    "马": "馬", "鸟": "鳥", "车": "車",
}

# 会意字的构件拆法（依字源，非从 docx 的「可拆部件」照抄——
# docx 那一栏写的是身体部位「门齿/长尾」，不是甲骨构件）。
# 只列字库里真有的构件；拆不出忠实构件的（羅 牧 化 死 出）宁可不收。
COMPOUND = {
    "武": ["止", "戈"], "戍": ["人", "戈"], "獲": ["又", "隹"], "鳴": ["口", "隹"],
    "家": ["宀", "豕"], "男": ["田", "力"], "步": ["止", "止"], "涉": ["水", "止"],
    "取": ["耳", "又"], "見": ["目", "人"], "囚": ["囗", "人"], "年": ["禾", "人"],
    "明": ["日", "月"], "从": ["人", "人"], "及": ["又", "人"], "休": ["人", "木"],
    "好": ["女", "子"], "采": ["又", "木"], "集": ["隹", "木"], "安": ["宀", "女"],
    "光": ["人", "火"], "析": ["木", "斤"], "相": ["木", "目"], "保": ["人", "子"],
    "逐": ["止", "豕"], "牢": ["宀", "牛"], "森": ["木", "木", "木"],
    "眾": ["日", "人", "人", "人"], "北": ["人", "人"], "朋": ["贝", "贝"],
}


def slug(pinyin):
    s = unicodedata.normalize("NFD", pinyin or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z]", "", s).lower() or "x"


def glyph_key(ch, parts):
    if ch in parts:
        return ch
    alt = ALIAS.get(ch)
    if alt and alt in parts:
        return alt
    return None


def main():
    codex = json.loads(io.open(CODEX, encoding="utf-8").read())
    parts = json.loads(io.open(GLYPHS, encoding="utf-8").read())["parts"]

    files = sorted(f for f in os.listdir(ARTDIR) if f.endswith(".png"))
    entries, tally, missing_art = [], {"stroke": 0, "compound": 0, None: 0}, []

    for i, e in enumerate(codex["entries"], start=1):
        want = "%02d-%s.png" % (i, slug(e["py"]))
        if want not in files:
            missing_art.append(e["char"])
        gk = glyph_key(e["char"], parts)
        comps = COMPOUND.get(e["char"])
        if gk:
            kind = "stroke"
        elif comps and all(c in parts for c in comps):
            kind = "compound"
        else:
            kind, comps = None, None
        tally[kind] += 1
        entries.append({
            "char": e["char"], "alt": e["alt"], "py": e["py"], "group": e["group"],
            "art": "assets/boss/" + want,
            "form": e["form"],
            "parts": e["parts"],
            "play": e["play"],
            "glyph": gk,
            "seg": parts[gk]["pieceCount"] if gk else 0,
            "playable": kind,
            "comps": comps or [],
        })

    doc = json.loads(io.open(LEVELS, encoding="utf-8").read())
    doc["bossCodex"] = {
        "_note": "《Boss（象形会意假借）.docx》的字表：形象 / 可拆部件 / 破解玩法。"
                 "art 指向 assets/boss/ 下的形象；glyph 是字库里对应的整字甲骨形（无则 null）；"
                 "playable 说明能不能真打成关卡——不臆造字形，拆不出忠实构件的只作名录。",
        "_version": "1.0",
        "_source": codex.get("_source", ""),
        "groups": codex["groups"],
        "entries": entries,
    }
    io.open(LEVELS, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, ensure_ascii=False, indent=1))

    print("已写入 levels.json 的 bossCodex 段：")
    for g in codex["groups"]:
        n = len([e for e in entries if e["group"] == g["id"]])
        print("  %-8s %-10s %2d 字" % (g["id"], g["name"], n))
    print("  合计 %d 字" % len(entries))
    print()
    print("  可打性：斩笔画 %d 个 / 拆构件 %d 个 / 仅名录 %d 个"
          % (tally["stroke"], tally["compound"], tally[None]))
    if missing_art:
        print("  ★ 缺形象资产：%s" % " ".join(missing_art))
    else:
        print("  形象资产：88 张全在 ✓")


if __name__ == "__main__":
    main()
