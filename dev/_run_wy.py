# -*- coding: utf-8 -*-
"""王邑闯关：浏览器内功能验证。
把 dev/wy-drive.js 注入 index.html 末尾运行，结果写入 data-report 后取回，
同时留一张地图截图便于人工核对。
用法：python dev/_run_wy.py
"""
import io, os, re, shutil, subprocess, sys

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)

# 浏览器隔离自检：必须用本项目自己的 profile。
# 教训——曾用「进程名 + 启动时间」过滤去关无头实例，把用户当时正在用的
# 浏览器一起强杀了。正确做法是按命令行里的 --user-data-dir 精确区分；
# 而且 headless 跑完通常自行退出，多数情况压根不需要清理。
# 若要清理，请用 dev/_cleanup_edge.py（它只认本项目 profile，且有演练模式）。
PROFILE = os.path.join(OUT, "wyprofile")
if not PROFILE.startswith(OUT + os.sep):
    raise SystemExit("浏览器 profile 不在项目 _check/ 内，拒绝运行：" + PROFILE)

src_drive = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wy-drive.js")
if not os.path.exists(src_drive):
    raise SystemExit("缺少驱动脚本：" + src_drive)

# 先做语法自检：括号失衡时 Node 会把错误报到下一行，极易误判。
# （本项目为此栽过跟头：一次粗糙替换改坏括号，排查被带偏很久。）
NODE = shutil.which("node")
if NODE:
    chk = subprocess.run([NODE, "--check", src_drive], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if chk.returncode != 0:
        print("驱动脚本语法有误，先修它：")
        print((chk.stderr or "").strip()[:600])
        sys.exit(1)
else:
    print("（未找到 node，跳过驱动语法自检）")

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
                    "--user-data-dir=" + PROFILE,
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

# 主报告取回后，再单独跑一次「只截地图」：
# 探针容器挂在 #sceneRoot 之后，窗口高度不够时会落到视野之外，
# 所以截图页把首页场景隐藏、只留探针，才能拍到地图本身。
shot_page = os.path.join(NEW, "_wy_shot.html")
io.open(shot_page, "w", encoding="utf-8").write(
    src.replace("</body>",
                "<script>\n" + code + "\n"
                "/* 截图专用：驱动跑完后隐藏首页场景，把探针地图挪到最前 */\n"
                "setTimeout(function(){\n"
                "  var sc = document.getElementById('sceneRoot');\n"
                "  if (sc) { sc.style.display = 'none'; }\n"
                "  var h = document.getElementById('wyProbeHost');\n"
                "  if (h && h.parentNode) { h.parentNode.insertBefore(h, document.body.firstChild); }\n"
                "  window.scrollTo(0, 0);\n"
                "}, 2600);\n"
                "</script>\n</body>", 1))
r2 = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                     "--user-data-dir=" + PROFILE,
                     "--window-size=1000,800",
                     "--screenshot=" + shot,
                     "--virtual-time-budget=20000", "--dump-dom",
                     "file:///" + shot_page.replace("\\", "/")],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=300)

for f in (tmp_path, shot_page):
    try:
        os.remove(f)
    except OSError:
        pass

print("已写出 _check/wy_report.txt | dom", len(c), "| exit", r.returncode,
      "| 截图", os.path.getsize(shot) if os.path.exists(shot) else 0, "B")
