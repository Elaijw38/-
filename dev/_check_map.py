import io, json, os, math
REPO = r"C:\DSH\字趣"
d = json.loads(io.open(os.path.join(REPO,"js","core","levels.json"), encoding="utf-8").read())
gl = json.loads(io.open(os.path.join(REPO,"js","core","glyph-parts.json"), encoding="utf-8").read())
m = d["map"]
vb = [int(v) for v in m["viewBox"].split()]
VW, VH = vb[2], vb[3]
objs = []
for z in m["zones"]:
    for o in z["objects"]:
        objs.append((z["id"], z["name"], o))

print("画布 %dx%d   实物 %d 个   底图 %s" % (VW, VH, len(objs), m["bgImage"]))
print("底图存在: %s  %.2f MB" % (os.path.exists(os.path.join(REPO, m["bgImage"])),
      os.path.getsize(os.path.join(REPO, m["bgImage"]))/1048576 if os.path.exists(os.path.join(REPO,m["bgImage"])) else 0))

miss = [o["char"] for _,_,o in objs if o["char"] not in gl["parts"]]
print("缺字形  : %s" % ("、".join(miss) if miss else "无 ✓"))

chs = [o["char"] for _,_,o in objs]
dup = [c for c in set(chs) if chs.count(c) > 1]
print("重复摆放: %s" % ("、".join(dup) if dup else "无 ✓"))

oob = ["%s(%d,%d r%d)" % (o["char"],o["x"],o["y"],o["r"]) for _,_,o in objs
       if o["x"]-o["r"] < 0 or o["y"]-o["r"] < 0 or o["x"]+o["r"] > VW or o["y"]+o["r"] > VH]
print("越出画布: %s" % ("；".join(oob) if oob else "无 ✓"))

ov = []
for i in range(len(objs)):
    for j in range(i+1, len(objs)):
        a, b = objs[i][2], objs[j][2]
        dd = math.hypot(a["x"]-b["x"], a["y"]-b["y"])
        if dd < (a["r"]+b["r"]) * 0.75:
            ov.append("%s(%d,%d)↔%s(%d,%d) 距%.0f 阈%.0f" % (a["char"],a["x"],a["y"],b["char"],b["x"],b["y"],dd,(a["r"]+b["r"])*0.75))
print("热区重叠: %s" % ("；".join(ov) if ov else "无 ✓"))
print("半径范围: %d ~ %d" % (min(o["r"] for _,_,o in objs), max(o["r"] for _,_,o in objs)))
print()
for z in m["zones"]:
    print("  %-8s %2d 个  %s" % (z["name"], len(z["objects"]), z["note"]))