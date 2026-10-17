# -*- coding: utf-8 -*-
"""把 js/core/demo.js 接进 index.html（放在 atlas.js 之前，shell.js 之后加载也行）。"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")
t = io.open(P, encoding="utf-8").read()
tag = '<script src="js/core/demo.js?v=20261017-1"></script>'
if tag in t:
    print("  已存在，跳过")
else:
    anchor = '<script src="js/core/atlas.js'
    assert t.count(anchor) == 1, t.count(anchor)
    t = t.replace(anchor, tag + "\n" + anchor, 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(t)
    print("  ✓ demo.js 已插入 index.html（atlas.js 之前）")
