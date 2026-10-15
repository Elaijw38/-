# -*- coding: utf-8 -*-
"""线上核验：确认推上去的东西**在线上真的生效、页面真的还能用**。

分两层，缺一层都不够：

1. **内容层**——本地文件与线上同路径文件逐字节比大小。
   为什么不能只看提交 sha：GitHub Pages 是异步构建的，提交成功后还有
   1~2 分钟构建窗口，期间线上仍是旧文件。只看 sha 就宣布上线，
   用户刷新到的还是老版本。
2. **功能层**——用真浏览器逐个打开线上八个页面，看 DOM 建没建起来、
   有没有"加载出错 / 该玩法尚未实现 / Uncaught"。

用法：
    python dev/_live_check.py                # 内容层关键文件 + 功能层八页
    python dev/_live_check.py --content      # 只做内容层（快）
    python dev/_live_check.py --pages        # 只做功能层
    python dev/_live_check.py --all          # 内容层查仓库全部文件
    python dev/_live_check.py --wait         # 内容没生效就轮询，最多等 10 分钟
    python dev/_live_check.py --needle "js/modes/boss-raid.js=POOL_SIZE"
"""
import argparse
import os
import re
import subprocess
import sys
import time

import requests

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "_check")
BASE = "https://elaijw38.github.io/jiagugouciji/"

SKIP_DIRS = {"_check", "_bak", "_edgeprof", "_docpages", "__pycache__", ".git"}
HTTP_H = {"Cache-Control": "no-cache", "Pragma": "no-cache",
          "User-Agent": "Mozilla/5.0 (compatible; live-check)"}

# 改动最频繁、最值得盯的几个
KEY_FILES = [
    "index.html",
    "js/core/_data.js",
    "js/core/levels.json",
    "js/core/atlas.js",
    "js/core/shell.js",
    "js/modes/boss-raid.js",
    "css/modes.css",
    "css/ui.css",
]

PAGES = [
    ("主页", ""), ("开始游戏", "#/modes"), ("汉字图鉴", "#/atlas"),
    ("玩法说明", "#/howto"), ("设置", "#/settings"),
    ("甲骨构字", "#/play/bone-build"), ("殷商王邑", "#/play/wangyi-map"),
    ("构件讨伐", "#/play/boss-raid"),
]


def tracked_files():
    out = []
    for dp, dns, fns in os.walk(REPO):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith(".pyc"):
                continue
            out.append(os.path.relpath(os.path.join(dp, fn), REPO).replace("\\", "/"))
    return sorted(out)


def content_pass(paths, needles):
    """本地与线上逐字节比大小。GitHub Pages 直接吐原始字节，不做转换。"""
    bad = []
    print("  %-32s %11s %11s  %s" % ("文件", "本地字节", "线上字节", "结果"))
    for rel in paths:
        local_p = os.path.join(REPO, rel.replace("/", os.sep))
        if not os.path.exists(local_p):
            print("  %-32s %11s %11s  %s" % (rel, "-", "-", "本地没有这个文件"))
            bad.append(rel)
            continue
        size = os.path.getsize(local_p)
        try:
            r = requests.get(BASE + rel, headers=HTTP_H, timeout=120)
        except Exception as e:
            print("  %-32s %11d %11s  %s" % (rel, size, "-", "取不到：%s" % e))
            bad.append(rel)
            continue
        live = len(r.content)
        if r.status_code != 200:
            verdict = "HTTP %s" % r.status_code
            bad.append(rel)
        elif live != size:
            verdict = "！不一致（线上还是旧版）"
            bad.append(rel)
        else:
            verdict = "一致"
        print("  %-32s %11d %11d  %s" % (rel, size, live, verdict))

    for rel, needle in needles:
        try:
            hit = needle in requests.get(BASE + rel, headers=HTTP_H, timeout=120).text
        except Exception:
            hit = False
        print("  断言 %-26s 含「%s」：%s" % (rel, needle, "是" if hit else "否"))
        if not hit:
            bad.append(rel + "=" + needle)
    return bad


def pages_pass():
    """逐个打开线上页面。判据是保守的：出现任何已知错误字样就算失败。"""
    os.makedirs(os.path.join(OUT, "ui"), exist_ok=True)
    prof = os.path.join(OUT, "liveprof")
    bad = 0
    for name, h in PAGES:
        r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                            "--user-data-dir=" + prof, "--disk-cache-size=1",
                            "--window-size=1280,1000", "--virtual-time-budget=22000",
                            "--dump-dom", BASE + h],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=260)
        d = r.stdout or ""
        err = ("加载出错" in d) or ("该玩法尚未实现" in d) or ("Uncaught" in d)
        if err:
            bad += 1
        m = re.search(r'<div class="scene([^"]*)"', d)
        print("  %-10s dom %7d  场景 %-22s 报错=%s"
              % (name, len(d), (m.group(1).strip() if m else "?"), "有" if err else "无"))
    print("  功能层：%s" % ("八页全正常" if bad == 0 else "%d 个页面有问题" % bad))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true", help="内容层查仓库全部文件")
    ap.add_argument("--content", action="store_true", help="只做内容层")
    ap.add_argument("--pages", action="store_true", help="只做功能层")
    ap.add_argument("--needle", action="append", default=[],
                    help="额外断言，格式 路径=字符串（可多次）")
    ap.add_argument("--wait", action="store_true", help="内容没生效就轮询，最多 10 分钟")
    a = ap.parse_args()

    both = not a.content and not a.pages
    paths = a.paths or (tracked_files() if a.all else KEY_FILES)
    needles = []
    for spec in a.needle:
        rel, _, s = spec.partition("=")
        needles.append((rel, s))

    print("线上站点：%s\n" % BASE)
    rc = 0

    if both or a.content:
        print("① 内容层：本地 vs 线上（%d 个文件）" % len(paths))
        deadline = time.time() + 600 if a.wait else time.time()
        attempt = 0
        while True:
            attempt += 1
            if attempt > 1:
                print("第 %d 次核对…" % attempt)
            bad = content_pass(paths, needles)
            if not bad:
                print("  内容层：线上与本地完全一致\n")
                break
            if time.time() >= deadline:
                print("  内容层：未生效 %d 处：%s" % (len(bad), bad[:8]))
                print("  等久了还不一致，去仓库 Actions / Pages 看构建有没有报错。\n")
                rc = 1
                break
            print("  还差 %d 处，等 20 秒再探（Pages 构建中）…\n" % len(bad))
            time.sleep(20)

    if both or a.pages:
        print("② 功能层：真浏览器逐个打开线上页面")
        rc = max(rc, 1 if pages_pass() else 0)
        print()

    print("结论：%s" % ("线上核验通过" if rc == 0 else "线上核验未通过，见上面明细"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
