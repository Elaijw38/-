# -*- coding: utf-8 -*-
"""功能验证：加载独立驱动脚本（不注入 HTML），结果写入 data-report 属性后取回。"""
import io, os, re, shutil, subprocess

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)

# 把驱动脚本放到 index.html 同级目录，作为最后一个 script 加载
src_drive = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive.js")
dst_drive = os.path.join(NEW, "_drive.js")
if not os.path.exists(src_drive):
    raise SystemExit("缺少驱动脚本：" + src_drive)
shutil.copyfile(src_drive, dst_drive)

src = io.open(os.path.join(NEW, "index.html"), encoding="utf-8").read()
tmp = src.replace('<script src="js/core/build.js"></script>',
                  '<script src="js/core/build.js"></script>\n<script src="_drive.js"></script>', 1)
tmp_path = os.path.join(NEW, "_drive.html")
io.open(tmp_path, "w", encoding="utf-8").write(tmp)

url = "file:///" + tmp_path.replace("\\", "/")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + os.path.join(OUT, "edgeprofile"),
                    "--virtual-time-budget=12000", "--dump-dom", url],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=240)
c = r.stdout or ""
io.open(os.path.join(OUT, "drive_dom.html"), "w", encoding="utf-8").write(c)

m = re.search(r'data-report="(.*?)"', c, re.S)
rep = m.group(1) if m else "(未取到 data-report)"
rep = (rep.replace("&quot;", '"').replace("&#39;", "'").replace("&#10;", "\n")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
io.open(os.path.join(OUT, "func_report.txt"), "w", encoding="utf-8").write(rep)

for f in (dst_drive, tmp_path):
    try:
        os.remove(f)
    except OSError:
        pass

print("已写出 _check/func_report.txt | dom", len(c), "| exit", r.returncode)
