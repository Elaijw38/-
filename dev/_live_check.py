# -*- coding: utf-8 -*-
"""线上功能实测：逐个打开线上页面，看是否正常、有无报错，并出一张首页截图。"""
import os, re, subprocess

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = r"C:\DSH\字趣\_check"
BASE = "https://elaijw38.github.io/jiagugouciji/"
PROF = os.path.join(OUT, "liveprof")

PAGES = [
    ("主页", ""), ("开始游戏", "#/modes"), ("汉字图鉴", "#/atlas"),
    ("玩法说明", "#/howto"), ("设置", "#/settings"),
    ("甲骨构字", "#/play/bone-build"), ("殷商王邑", "#/play/wangyi-map"),
    ("构件讨伐", "#/play/boss-raid"),
]

bad = 0
for name, h in PAGES:
    r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                        "--user-data-dir=" + PROF, "--disk-cache-size=1",
                        "--window-size=1280,1000", "--virtual-time-budget=22000", "--dump-dom",
                        BASE + h],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=260)
    d = r.stdout or ""
    err = ("加载出错" in d) or ("该玩法尚未实现" in d) or ("Uncaught" in d)
    if err:
        bad += 1
    m = re.search(r'<div class="scene([^"]*)"', d)
    print("  %-10s dom %7d  场景 %-22s 报错=%s" % (
        name, len(d), (m.group(1).strip() if m else "?"), "有 X" if err else "无"))

print()
print("  结论：%s" % ("线上八个页面全部正常 OK" if bad == 0 else "%d 个页面有问题 X" % bad))

# 线上首页首屏截图
png = os.path.join(OUT, "ui", "live_home.png")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + PROF + "shot", "--disk-cache-size=1",
                    "--window-size=1440,900", "--screenshot=" + png,
                    "--virtual-time-budget=22000", "--dump-dom", BASE],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=260)
d = r.stdout or ""
print()
print("  线上首页断言：")
print("    整屏大图 .hero-bg : %s" % ("有" if 'class="hero-bg"' in d else "无"))
print("    压暗层 .hero-veil : %s" % ("有" if 'hero-veil' in d else "无"))
print("    下滑提示          : %s" % ("有" if 'hero-cue' in d else "无"))
print("    成就项 .ach-item  : %d 个" % d.count('class="ach-item'))
print("    评级别 .cc-rankname: %s" % ("有" if 'cc-rankname' in d else "无"))
print("    玩法卡 .play-card : %d 个" % d.count('class="play-card"'))
print("    截图 %s  %d B" % (png, os.path.getsize(png) if os.path.exists(png) else 0))
