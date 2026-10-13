# -*- coding: utf-8 -*-
"""盘点第二关字表：逐字核对甲骨字形覆盖情况，并列出物件与场景位置。

只读，不改任何文件。
数据来源：
  · 字表与坐标 = js/core/_data.js 里 App.levels.map.zones[].objects
  · 甲骨字形     = js/core/_data.js 里 App.glyphs.parts（73 字，CC BY 4.0）
"""
import io
import json
import os

REPO = r"C:\DSH\字趣"
P = os.path.join(REPO, "js", "core", "_data.js")
t = io.open(P, encoding="utf-8").read()


def json_span(text, start):
    depth = 0
    i = start
    in_str = False
    esc = False
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1
        i += 1
    raise SystemExit("brace mismatch")


HEAD = "App.levels = "
i = t.index(HEAD) + len(HEAD)
a, b = json_span(t, t.index("{", i))
levels = json.loads(t[a:b])

# glyphs
gi = t.index("App.glyphs = ")
ga, gb = json_span(t, t.index("{", gi))
glyphs = json.loads(t[ga:gb])
parts = set(glyphs["parts"].keys())

zones = levels["map"]["zones"]
have, missing = [], []
for z in zones:
    for o in z["objects"]:
        (have if o["char"] in parts else missing).append((z["name"], o["char"]))

print("  字形来源：%s" % glyphs["attribution"]["dataset"])
print("            %s / 授权 %s / DOI %s"
      % (glyphs["attribution"]["authors"], glyphs["attribution"]["license"],
         glyphs["attribution"]["doi"]))
print("  数据集共 %d 字；第二关 %d 字中：有字形 %d，无字形 %d"
      % (len(parts), len(have) + len(missing), len(have), len(missing)))
print()
print("  无甲骨字形的字（必须用构件组合示意，且需标注）：")
if missing:
    for zn, c in missing:
        print("    %-8s %s" % (zn, c))
else:
    print("    （无）")
print()
print("  有甲骨字形的字：")
line = []
for zn, c in have:
    line.append(c)
print("    " + " ".join(line))
