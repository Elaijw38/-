# -*- coding: utf-8 -*-
"""撤掉已经没人用的底纹生成代码。

背景：页面地色曾经有三层（刻辞底纹 + 骨材质 + 竖向渐变），
`build.js` 里的 `buildPatternURI()` / `injectPattern()` 就是为第一层服务的。
现在地色按三家美术馆规范退回**平的骨色**（见 css/theme.css 的 body），
`--ob-pattern` 在 CSS 里已经没有引用，这两段代码成了死代码：
每次启动仍要合成一张 860×860 的 SVG（24081 字符）+ 一次 encodeURIComponent，
纯白烧。

本步只删死代码，不动别的。删完由 _syntax_probe / _verify_deploy 兜底。
"""
import io

P = r"C:\DSH\字趣\js\core\build.js"
t = io.open(P, encoding="utf-8").read()
before = len(t)

START = "  /* ============================================================\n" \
        "     页面底纹：真实甲骨文字形，竖排成列"
END = "  /* ---------- 启动 ---------- */"

i = t.find(START)
j = t.find(END)
if i < 0 or j < 0 or j <= i:
    raise SystemExit("!! 定位失败：START=%d END=%d" % (i, j))

removed = t[i:j]
t = t[:i] + t[j:]

OLD_BOOT = "  function boot() {\n    injectPattern();\n    applyAppearance();"
NEW_BOOT = "  function boot() {\n    applyAppearance();"
if OLD_BOOT not in t:
    raise SystemExit("!! boot() 里的 injectPattern() 调用没找到，先看清楚再改")
t = t.replace(OLD_BOOT, NEW_BOOT, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)

print("  删掉 %d 字符（%d 行）" % (len(removed), removed.count("\n")))
print("  文件 %d → %d 字符" % (before, len(t)))
for name in ("injectPattern", "buildPatternURI", "--ob-pattern", "patRand"):
    print("  残留 %-16s %d 处 %s" % (name, t.count(name), "OK" if t.count(name) == 0 else "X"))
