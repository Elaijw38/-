# -*- coding: utf-8 -*-
"""一次性补丁：把 .wy2-viewport 的高度改成"扣掉固定顶栏"的口径。

为什么单独写个脚本：这条 CSS 里含 `calc(100vh - 300px)` 与括号，
直接在命令行里替换会被 PowerShell 的引号规则吃掉（这个项目已经踩过一次）。
写成文件跑，稳。

用法：python dev/_patch_viewport_h.py
"""
import io
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(REPO, "css", "modes.css")

OLD = (
    "/* 视口：手机上图很大，这里给它一个固定的可滚动窗口，方便拖动看图 */\n"
    ".wy2-viewport { position: relative; overflow: auto; margin-top: 10px;\n"
    "  height: clamp(320px, calc(100vh - 300px), 720px);\n"
    "  background: var(--bone1); border: 1px solid var(--edge);\n"
    "  touch-action: pan-x pan-y; overscroll-behavior: contain;\n"
    "  -webkit-overflow-scrolling: touch; }\n"
)

NEW = (
    "/* 视口：手机上图很大，这里给它一个固定的可滚动窗口，方便拖动看图。\n"
    "   高度必须**扣掉固定顶栏**（约 58px）：否则图的边缘会滚到顶栏底下，\n"
    "   那一带的热点就永远点不到——实测「宀」滚到 y=54 时被顶栏吃掉，\n"
    "   点击直接落到顶栏的导航链接上。 */\n"
    ".wy2-viewport { position: relative; overflow: auto; margin-top: 10px;\n"
    "  height: clamp(300px, calc(100vh - 268px), 700px);\n"
    "  max-height: calc(100vh - 76px);\n"
    "  background: var(--bone1); border: 1px solid var(--edge);\n"
    "  touch-action: pan-x pan-y; overscroll-behavior: contain;\n"
    "  -webkit-overflow-scrolling: touch;\n"
    "  scroll-margin-top: 76px; }\n"
)

t = io.open(CSS, encoding="utf-8").read()
n = t.count(OLD)
if n != 1:
    raise SystemExit("!! 命中 %d 次，预期 1 次，拒绝写入" % n)
io.open(CSS, "w", encoding="utf-8", newline="\n").write(t.replace(OLD, NEW))
print("  已改 .wy2-viewport 高度口径（扣掉固定顶栏）")
