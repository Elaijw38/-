# -*- coding: utf-8 -*-
"""精确定位 <main id="sceneRoot"> 是否被填充，并抽取脚本执行线索。"""
import io, os, re, subprocess

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
url = "file:///" + os.path.join(NEW, "index.html").replace("\\", "/")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + os.path.join(NEW, "_check", "edgeprofile"),
                    "--virtual-time-budget=6000", "--dump-dom", url],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=150)
c = r.stdout or ""
io.open(os.path.join(NEW, "_check", "raw2.html"), "w", encoding="utf-8").write(c)

m = re.search(r'<main\b[^>]*>(.*?)</main>', c, re.S)
print("=== <main> 匹配:", bool(m))
if m:
    inner = m.group(1)
    print("main 内部长度:", len(inner.strip()))
    print("main 内部（前 600 字符）:")
    print(inner[:600] or "(空)")

print()
print("=== body 里是否有 .scene / .home-card ===")
print("出现 .scene:", 'class="scene' in c)
print("出现 home-grid:", 'home-grid' in c)
print("出现 siteTop 内部:", c.count('class="top-left"'))
print()
print("=== 总的 DOM 长度:", len(c))
