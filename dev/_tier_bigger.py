# -*- coding: utf-8 -*-
"""徽记放大：拼合档字形间距收紧、纠缠档放大、独体档撑满。"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "js", "modes", "boss-raid.js")
t = io.open(P, encoding="utf-8").read()
pairs = [
    ("var n = list.length, gap = 6;", "var n = list.length, gap = 2;"),
    ("scale(.74)", "scale(.86)"),
    ("translate(6,3) scale(.88)", "translate(2,1) scale(.96)"),
]
n = 0
for old, new in pairs:
    if t.count(old) == 1:
        t = t.replace(old, new)
        n += 1
    else:
        print("  跳过（命中 %d 次）：%s" % (t.count(old), old))
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("  已改 %d 处" % n)
