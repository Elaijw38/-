# -*- coding: utf-8 -*-
"""检查玩法挂载后的 DOM：host 是否存在、setup 是否有内容、卡片文本。"""
import io, os, re, subprocess

NEW = r"C:\DSH\字趣"
OUT = os.path.join(NEW, "_check")
c = io.open(os.path.join(OUT, "drive_dom.html"), encoding="utf-8").read()

for tag in ['<main', '<div class="mode-host"', 'class="setup"', 'class="sect"',
            'class="scene play-scene"', 'id="mpPieces"']:
    print("%-32s 出现 %d 次" % (tag, c.count(tag)))

print()
m = re.search(r'<main\b[^>]*>(.*?)</main>', c, re.S)
if m:
    inner = m.group(1)
    print("main 内部长度:", len(inner.strip()))
    print("main 内部（前 1200 字符）:")
    print(inner[:1200] if inner.strip() else "(空)")
else:
    print("未匹配 <main>")

print()
print("=== 页脚之前是否还有 scene ===")
i = c.find('<footer')
seg = c[max(0, i - 1500):i]
print(seg[-1200:])
