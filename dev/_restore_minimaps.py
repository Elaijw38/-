# -*- coding: utf-8 -*-
"""把页面素材恢复为「更早一版」（out/minimaps/_original/）。

背景：我本轮把五张换成了"等距地形图"画法，用户判断为变差。
用户明确指定以 _original 那一版为基础继续。
本步只做恢复，不改画面、不加效果、不再换画法。

被撤下的版本移到 out/_rejected/ 留档（不删，便于回溯）。
"""
import os
import shutil

REPO = r"C:\DSH\字趣"
DST = os.path.join(REPO, "out", "minimaps")
ORI = os.path.join(DST, "_original")
REJ = os.path.join(REPO, "out", "_rejected")
os.makedirs(REJ, exist_ok=True)

NAMES = ["minimap-01-天象.jpg", "minimap-02-山川.jpg", "minimap-03-草木.jpg",
         "minimap-04-禽兽虫鱼.jpg", "minimap-05-人居器物.jpg"]

print("  恢复 _original -> out/minimaps/")
for n in NAMES:
    src = os.path.join(ORI, n)
    dst = os.path.join(DST, n)
    if not os.path.exists(src):
        print("    !! 备份缺失 %s" % n)
        continue
    # 先把当前（被否的）版本挪去留档，再恢复
    if os.path.exists(dst):
        shutil.move(dst, os.path.join(REJ, n))
    shutil.copy2(src, dst)
    print("    %-28s %8d B" % (n, os.path.getsize(dst)))

# 本轮生成的地图版也一并挪去留档，避免以后再混用
for n in sorted(os.listdir(os.path.join(REPO, "out", "mapstyle"))) \
        if os.path.isdir(os.path.join(REPO, "out", "mapstyle")) else []:
    if n.lower().endswith(".jpg"):
        shutil.move(os.path.join(REPO, "out", "mapstyle", n), os.path.join(REJ, "mapstyle-" + n))
print("\n  被撤下的版本留档在 %s" % REJ)
for n in sorted(os.listdir(REJ)):
    print("    %s" % n)

# 复核：页面素材现在的尺寸与来源
from PIL import Image
print("\n  页面当前素材：")
for n in NAMES:
    im = Image.open(os.path.join(DST, n))
    print("    %-28s %s  16:9=%s" % (n, "%dx%d" % im.size,
                                     "是" if abs(im.size[0] / im.size[1] - 16 / 9) < 0.01 else "否"))
