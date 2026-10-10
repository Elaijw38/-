# -*- coding: utf-8 -*-
"""看探针版页面的真实 DOM：sceneRoot 内容与控制台错误。"""
import io, os, re, subprocess

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
p = os.path.join(NEW, "_check", "probe.html")
url = "file:///" + p.replace("\\", "/")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + os.path.join(NEW, "_check", "edgeprofile"),
                    "--virtual-time-budget=8000", "--dump-dom", url],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=150)
c = r.stdout or ""
io.open(os.path.join(NEW, "_check", "raw_probe.html"), "w", encoding="utf-8").write(c)

i = c.find('id="sceneRoot"')
print("sceneRoot 位置:", i)
if i > 0:
    print(repr(c[i:i + 900]))
print()
m = re.search(r'<pre id="__report"[^>]*>(.*?)</pre>', c, re.S)
print("=== 探针报告 ===")
print((m.group(1) if m else "(无)")[:1200])
