# -*- coding: utf-8 -*-
"""截取各页面（观感自查）
   要点：不靠运行时改 hash（虚拟时间下不可靠），而是把 hash 直接写在文件 URL 上。
        同时用 CSS zoom 把整页缩小，以便在 171px 的小视口里看到更多内容。"""
import io, os, subprocess
from PIL import Image

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)
ud = os.path.join(OUT, "edgeprofile")

# (名称, hash, 缩放)
PAGES = [
    ("p_home",     "",                1.0),
    ("p_home_z",   "",                0.42),
    ("p_modes_z",  "#/modes",         0.42),
    ("p_play_z",   "#/play/bone-build", 0.42),
    ("p_settings_z", "#/settings",    0.42),
    ("p_plan_z",   "#/plan",          0.42),
]

src = io.open(os.path.join(NEW, "index.html"), encoding="utf-8").read()

for name, hash_, zoom in PAGES:
    if zoom != 1.0:
        inj = ('<style>html{zoom:%s}</style>\n' % zoom)
    else:
        inj = ''
    page = src.replace("</head>", inj + "</head>", 1) if inj else src
    p = os.path.join(NEW, "_shot_" + name + ".html")
    io.open(p, "w", encoding="utf-8").write(page)
    png = os.path.join(OUT, name + ".png")
    url = "file:///" + p.replace("\\", "/") + hash_
    r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        "--force-device-scale-factor=2",
                        "--user-data-dir=" + ud,
                        "--screenshot=" + png,
                        "--virtual-time-budget=8000", url],
                       capture_output=True, timeout=200)
    if not os.path.exists(png):
        print(name, "失败", (r.stderr or "")[:150])
        continue
    im = Image.open(png)
    print("%-14s %s" % (name, im.size))

print("完成：", OUT)
