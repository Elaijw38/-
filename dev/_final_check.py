# -*- coding: utf-8 -*-
"""最终交付自检：本地八个页面是否都正常。"""
import os, re, subprocess

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"C:\DSH\字趣\_check"
URL = "file:///C:/DSH/%E5%AD%97%E8%B6%A3/index.html"

PAGES = [
    ("主页", ""), ("开始游戏", "#/modes"), ("汉字图鉴", "#/atlas"),
    ("玩法说明", "#/howto"), ("设置", "#/settings"),
    ("甲骨构字", "#/play/bone-build"), ("殷商王邑", "#/play/wangyi-map"),
    ("构件讨伐", "#/play/boss-raid"),
]

bad = 0
for name, h in PAGES:
    r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                        "--user-data-dir=" + os.path.join(OUT, "final"), "--disk-cache-size=1",
                        "--window-size=1280,1000", "--virtual-time-budget=15000", "--dump-dom",
                        URL + h],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=200)
    d = r.stdout or ""
    err = ("加载出错" in d) or ("该玩法尚未实现" in d) or ("Uncaught" in d)
    if err:
        bad += 1
    m = re.search(r'<div class="scene([^"]*)"', d)
    scene = (m.group(1).strip() if m else "?")
    print("  %-10s dom %7d   场景类 %-22s 报错=%s" % (
        name, len(d), scene, "有 X" if err else "无"))

print()
print("  结论：%s" % ("八个页面全部正常 OK" if bad == 0 else "%d 个页面有问题 X" % bad))
