# -*- coding: utf-8 -*-
"""新版壳层验证：把 dev/shell-drive.js 注入 index.html 末尾跑一遍。
用法：python dev/_run_shell.py
"""
import io, os, re, shutil, subprocess, sys

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)
PROFILE = os.path.join(OUT, "shellprof")
if not PROFILE.startswith(OUT + os.sep):
    raise SystemExit("profile 不在 _check 内，拒绝运行")

src_drive = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shell-drive.js")
NODE = shutil.which("node")
if NODE:
    chk = subprocess.run([NODE, "--check", src_drive], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if chk.returncode != 0:
        print("驱动脚本语法有误：")
        print((chk.stderr or "").strip()[:600])
        sys.exit(1)

code = io.open(src_drive, encoding="utf-8").read()
src = io.open(os.path.join(NEW, "index.html"), encoding="utf-8").read()
tmp = os.path.join(NEW, "_shell.html")
io.open(tmp, "w", encoding="utf-8").write(
    src.replace("</body>", "<script>\n" + code + "\n</script>\n</body>", 1))

r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + PROFILE, "--disk-cache-size=1",
                    "--window-size=1280,1000",
                    "--virtual-time-budget=22000", "--dump-dom",
                    "file:///" + tmp.replace("\\", "/")],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=300)
dom = r.stdout or ""
m = re.search(r'data-report="(.*?)"', dom, re.S)
rep = m.group(1) if m else "(未取到 data-report)"
rep = (rep.replace("&quot;", '"').replace("&#39;", "'").replace("&#10;", "\n")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
io.open(os.path.join(OUT, "shell_report.txt"), "w", encoding="utf-8").write(rep)
try:
    os.remove(tmp)
except OSError:
    pass
print("已写出 _check/shell_report.txt | dom %d | exit %d" % (len(dom), r.returncode))
