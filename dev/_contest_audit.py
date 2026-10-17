# -*- coding: utf-8 -*-
"""参赛自检：首屏负载、参赛材料、无障碍、体量分布。"""
import glob
import io
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)

t = io.open("index.html", encoding="utf-8").read()
srcs = re.findall(r'src="([^"]+)"', t) + re.findall(r'href="(css/[^"]+)"', t)
tot, files = 0, 0
for s in srcs:
    p = s.split("?")[0]
    if os.path.exists(p):
        tot += os.path.getsize(p)
        files += 1
print("  [首屏] 脚本+样式 %d 个文件，共 %.0f KB" % (files, tot / 1024))
hero = [p for p in glob.glob("assets/*") if "bone" in p.lower() or "hero" in p.lower()]
for p in hero[:4]:
    print("  [首屏] 大图 %-28s %6.0f KB" % (os.path.basename(p), os.path.getsize(p) / 1024))

print("\n  [体量] 各处占比：")
buckets = {}
for p in glob.glob("assets/**/*", recursive=True):
    if not os.path.isfile(p):
        continue
    key = "assets/boss(88张)" if "assets/boss" in p.replace("\\", "/") and os.path.basename(p)[:2].isdigit() else (
        "assets/六张地图" if "level2-" in os.path.basename(p) else "assets/其它")
    buckets[key] = buckets.get(key, 0) + os.path.getsize(p)
for k, v in sorted(buckets.items(), key=lambda x: -x[1]):
    print("    %-22s %6.1f MB" % (k, v / 1048576))

print("\n  [材料] 根目录里像参赛文档的文件：")
hit = False
for p in glob.glob("*"):
    if re.search(r"参赛|申报|评审|四创|材料|方案|PPT|\.md$", p) and os.path.isfile(p):
        print("    %-24s %7.0f B" % (p, os.path.getsize(p)))
        hit = True
if not hit:
    print("    （无）")

print("\n  [无障碍] index.html：")
print("    img %d 个，带 alt %d 个；aria- %d 处"
      % (len(re.findall(r"<img", t)), len(re.findall(r"<img[^>]*alt=", t)),
         len(re.findall(r"aria-", t))))

print("\n  [离线] 是否存在联网请求（fetch/XHR/CDN）：")
ext = []
for p in glob.glob("js/**/*.js", recursive=True) + ["index.html"]:
    s = io.open(p, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"(https?://[^\s\"'<>)]+)", s):
        u = m.group(1)
        if not re.search(r"w3\.org|creativecommons|doi\.org|zenodo|github\.com|wikimedia", u):
            ext.append((p, u))
if ext:
    for p, u in ext[:8]:
        print("    %s -> %s" % (p, u))
else:
    print("    无（纯本地资源，可离线/file:// 打开）")
