# -*- coding: utf-8 -*-
"""
把两个 JSON 内联进 js/core/_data.js，供 leveldata.js 使用。

为什么内联：平台要保证「双击 index.html 即可运行」，file:// 下 fetch 本地
JSON 会被 CORS 拦（origin 为 null），故改为 script 内联数据。

用法：python dev/_build_leveldata.py
"""
import io, json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = [
    ("levels", os.path.join(ROOT, "js", "core", "levels.json")),
    ("glyphs", os.path.join(ROOT, "js", "core", "glyph-parts.json")),
]
OUT = os.path.join(ROOT, "js", "core", "_data.js")

chunks = []
chunks.append("/* 由 dev/_build_leveldata.py 生成，请勿手改。\n"
              "   源：js/core/levels.json 与 js/core/glyph-parts.json */\n"
              "(function (App) {\n  'use strict';\n")
for name, path in SRC:
    doc = json.loads(io.open(path, "rb").read().decode("utf-8"))
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    # 防止 JSON 里的字符串意外闭合 </script>
    text = text.replace("</", "<\\/")
    chunks.append("  App.%s = %s;\n\n" % (name, text))
chunks.append("})(window.App = window.App || {});\n")

io.open(OUT, "w", encoding="utf-8").write("".join(chunks))
print("已写出:", OUT)
print("体积: %.1f KB" % (os.path.getsize(OUT) / 1024))
