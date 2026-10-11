# -*- coding: utf-8 -*-
"""构件讨伐（BOSS 战）：浏览器内功能验证。

把 dev/bo-drive.js 注入 index.html 末尾运行，结果写入 data-report 后取回，
另拍两张图：选 BOSS 页、合体 BOSS 战斗页。
用法：python dev/_run_bo.py
"""
import io, os, re, shutil, subprocess, sys

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)

# 浏览器隔离自检：必须用本项目自己的 profile（曾误杀用户浏览器，见 _run_wy.py 注释）
PROFILE = os.path.join(OUT, "boprofile")
if not PROFILE.startswith(OUT + os.sep):
    raise SystemExit("浏览器 profile 不在项目 _check/ 内，拒绝运行：" + PROFILE)

src_drive = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bo-drive.js")
if not os.path.exists(src_drive):
    raise SystemExit("缺少驱动脚本：" + src_drive)

# 先做语法自检：括号失衡时 Node 会把错误报到下一行，极易误判
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

code = io.open(src_drive, encoding="utf-8").read()
src = io.open(os.path.join(NEW, "index.html"), encoding="utf-8").read()
tmp_path = os.path.join(NEW, "_bo.html")
io.open(tmp_path, "w", encoding="utf-8").write(
    src.replace("</body>", "<script>\n" + code + "\n</script>\n</body>", 1))

url = "file:///" + tmp_path.replace("\\", "/")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + PROFILE,
                    "--window-size=1180,900",
                    "--virtual-time-budget=22000", "--dump-dom", url],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=300)
c = r.stdout or ""
io.open(os.path.join(OUT, "bo_dom.html"), "w", encoding="utf-8").write(c)

m = re.search(r'data-report="(.*?)"', c, re.S)
rep = m.group(1) if m else "(未取到 data-report)"
rep = (rep.replace("&quot;", '"').replace("&#39;", "'").replace("&#10;", "\n")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
io.open(os.path.join(OUT, "bo_report.txt"), "w", encoding="utf-8").write(rep)


def shoot(tag, js_setup):
    """单独跑一遍只截图：隐藏首页场景，把探针挂在最前，直接拍到 BOSS 界面。"""
    page = os.path.join(NEW, "_bo_shot.html")
    io.open(page, "w", encoding="utf-8").write(
        src.replace("</body>",
                    "<script>\n"
                    "setTimeout(function(){\n"
                    "  var sc = document.getElementById('sceneRoot');\n"
                    "  if (sc) { sc.style.display = 'none'; }\n"
                    "  var App = window.App;\n"
                    "  var h = document.createElement('div');\n"
                    "  h.id = 'boShotHost'; h.style.padding = '14px';\n"
                    "  document.body.insertBefore(h, document.body.firstChild);\n"
                    "  var m = App.modes.get('boss-raid');\n"
                    "  m.mount(h, App.modes.buildContext(m));\n"
                    + js_setup +
                    "  window.scrollTo(0, 0);\n"
                    "}, 1200);\n"
                    "</script>\n</body>", 1))
    png = os.path.join(OUT, tag + ".png")
    rr = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                         "--user-data-dir=" + PROFILE,
                         "--window-size=1180,900",
                         "--screenshot=" + png,
                         "--virtual-time-budget=14000", "--dump-dom",
                         "file:///" + page.replace("\\", "/")],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=300)
    try:
        os.remove(page)
    except OSError:
        pass
    return png, rr


def click_script(regex, times=1):
    return ("  var bs = h.querySelectorAll('button'), t = null;\n"
            "  for (var i = 0; i < bs.length; i++) { if (" + regex +
            ".test(bs[i].textContent)) { t = bs[i]; break; } }\n"
            "  for (var k = 0; k < " + str(times) + "; k++) { if (t) { t.click(); } }\n")


# 1) 选 BOSS 页
s1, _ = shoot("bo_pick", "")
# 2) 合体 BOSS「涉」战斗页（点第一个卡片）
s2, _ = shoot("bo_fight", "  var cards = h.querySelectorAll('.bo-card'); if (cards[0]) { cards[0].click(); }\n")
# 3) 终极「車」的身体（elite 第 8 个）
s3, _ = shoot("bo_elite",
              "  var cards = h.querySelectorAll('.bo-card'); if (cards[20]) { cards[20].click(); }\n")

try:
    os.remove(tmp_path)
except OSError:
    pass

print("已写出 _check/bo_report.txt | dom", len(c), "| exit", r.returncode)
for f in (s1, s2, s3):
    print("  截图 %s  %s B" % (os.path.basename(f),
                              os.path.getsize(f) if os.path.exists(f) else 0))
