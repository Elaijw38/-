# -*- coding: utf-8 -*-
"""王邑闯关：浏览器内功能验证。
把 dev/wy-drive.js 注入 index.html 末尾运行，结果写入 data-report 后取回，
同时留一张地图截图便于人工核对。
用法：python dev/_run_wy.py
"""
import io, os, re, shutil, subprocess

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)

src_drive = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wy-drive.js")
if not os.path.exists(src_drive):
    raise SystemExit("缺少驱动脚本：" + src_drive)

# 直接以 <script> 内联注入。不能用 <script src>：
# file:// 下加载同目录 js 没问题，但驱动要与平台同帧执行完毕，
# 内联可避免再多一次请求与潜在的顺序问题。
code = io.open(src_drive, encoding="utf-8").read()
src = io.open(os.path.join(NEW, "index.html"), encoding="utf-8").read()
tmp_path = os.path.join(NEW, "_wy.html")
io.open(tmp_path, "w", encoding="utf-8").write(
    src.replace("</body>", "<script>\n" + code + "\n</script>\n</body>", 1))

url = "file:///" + tmp_path.replace("\\", "/")
shot = os.path.join(OUT, "wy_map.png")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + os.path.join(OUT, "wyprofile"),
                    "--window-size=1000,940",
                    "--screenshot=" + shot,
                    "--virtual-time-budget=20000", "--dump-dom", url],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=300)
c = r.stdout or ""
io.open(os.path.join(OUT, "wy_dom.html"), "w", encoding="utf-8").write(c)

m = re.search(r'data-report="(.*?)"', c, re.S)
rep = m.group(1) if m else "(未取到 data-report)"
rep = (rep.replace("&quot;", '"').replace("&#39;", "'").replace("&#10;", "\n")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
io.open(os.path.join(OUT, "wy_report.txt"), "w", encoding="utf-8").write(rep)

try:
    os.remove(tmp_path)
except OSError:
    pass

print("已写出 _check/wy_report.txt | dom", len(c), "| exit", r.returncode)
