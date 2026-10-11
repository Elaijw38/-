# -*- coding: utf-8 -*-
"""新版壳层截图：桌面与移动两种宽度，覆盖首页/图鉴/玩法说明/游戏页。"""
import os, subprocess, sys

REPO = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(REPO, "_check", "ui")
os.makedirs(OUT, exist_ok=True)
PROFILE = os.path.join(REPO, "_check", "uiprof")
if not PROFILE.startswith(os.path.join(REPO, "_check") + os.sep):
    raise SystemExit("profile 不在 _check 内，拒绝运行")

PAGES = [
    ("home", "", ""),
    ("atlas", "#/atlas", ""),
    ("howto", "#/howto", ""),
    ("modes", "#/modes", ""),
    ("settings", "#/settings", ""),
    ("game-wangyi", "#/play/wangyi-map", ""),
    ("game-boss", "#/play/boss-raid", ""),
    ("game-bone", "#/play/bone-build", ""),
]
SIZES = [("d", 1280, 1000), ("m", 390, 844)]

for tag, w, h in SIZES:
    for name, hash_, _ in PAGES:
        url = "file:///C:/DSH/%E5%AD%97%E8%B6%A3/index.html" + hash_
        png = os.path.join(OUT, "%s_%s.png" % (name, tag))
        r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                            "--user-data-dir=" + PROFILE + tag, "--disk-cache-size=1",
                            "--window-size=%d,%d" % (w, h),
                            "--screenshot=" + png,
                            "--virtual-time-budget=16000", "--dump-dom", url],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=200)
        dom = r.stdout or ""
        err = "有错误" if ("加载出错" in dom or "Uncaught" in dom) else "无"
        size = os.path.getsize(png) if os.path.exists(png) else 0
        print("  [%s %4d] %-12s dom %6d  err=%s  png %7d" % (
            tag, w, name, len(dom), err, size))
print("\n截图目录：" + OUT)
