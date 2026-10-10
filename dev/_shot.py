# -*- coding: utf-8 -*-
"""用 headless Edge 截图新平台，并裁出可读的局部。
   Edge 的 --window-size 在部分版本会被忽略，这里以实际输出尺寸为准再做裁切。"""
import io, os, subprocess, sys
from PIL import Image

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)
ud = os.path.join(OUT, "edgeprofile")

TARGETS = [
    ("home",  "index.html",                      None),
    ("modes", "index.html#/modes",               None),
    ("plan",  "index.html#/plan",                None),
    ("settings", "index.html#/settings",         None),
]

def shot(name, rel, height):
    url = "file:///" + os.path.join(NEW, rel).replace("\\", "/")
    png = os.path.join(OUT, name + ".png")
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
           "--force-device-scale-factor=2",
           "--user-data-dir=" + ud,
           "--screenshot=" + png,
           "--virtual-time-budget=7000", url]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    if not os.path.exists(png):
        print("  !! 未生成", name, (r.stderr or "")[:200])
        return None
    im = Image.open(png)
    return im

for name, rel, h in TARGETS:
    im = shot(name, rel, h)
    if im:
        print("%-9s 截图 %s" % (name, im.size))
        # 裁掉大面积空白：按内容底部裁剪
        try:
            rgb = im.convert("RGB")
            w, hh = rgb.size
            # 找最后一行非背景色（背景为深色 #14100c 左右）
            bg = rgb.getpixel((5, 5))
            last = 0
            for y in range(hh - 1, 0, -30):
                row = [rgb.getpixel((x, y)) for x in range(0, w, 40)]
                if any(abs(px[0]-bg[0]) + abs(px[1]-bg[1]) + abs(px[2]-bg[2]) > 24 for px in row):
                    last = min(hh, y + 40)
                    break
            if last and last < hh:
                rgb.crop((0, 0, w, last)).save(png)
                print("           已裁到内容高度 %d" % last)
        except Exception as e:
            print("           裁切跳过:", str(e)[:60])

print("完成，输出目录:", OUT)
