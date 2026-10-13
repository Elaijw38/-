# -*- coding: utf-8 -*-
"""还原第二关的 61 个热区坐标，只保留 art 插画路径。

为什么必须还原 —— 坐标系搞错了：
  · 游戏内热区点在 assets/wangyi-map.jpg 上，空间是 **1800×1010**
    （map.viewBox = "0 0 1800 1010"），热区 x/y 都在这套坐标里手工标定。
  · 而 zones[].art 的分区插画是 2624×1472，只在小地图页当插画展示。
  · 我上一轮误把热区坐标按 **2624×1472** 重写了，坐标系不同，
    大部分点位会偏出实物（越靠右下偏得越多）。
  所以：坐标回滚到改动前的值，art 保留。

备份：_check/levels.json.bak 与 _check/_data.js.bak（我改动前存的）
"""
import io
import json
import os

REPO = r"C:\DSH\字趣"


def span(text, start):
    depth = 0
    i = start
    ins = esc = False
    while i < len(text):
        c = text[i]
        if ins:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                ins = False
        else:
            if c == '"':
                ins = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1
        i += 1
    raise SystemExit("brace mismatch")


# 1) 从备份读回原始坐标
bak = json.load(io.open(os.path.join(REPO, "_check", "levels.json.bak"),
                        encoding="utf-8"))
orig = {}
for z in bak["map"]["zones"]:
    orig[z["id"]] = {o["char"]: (o["x"], o["y"], o["r"]) for o in z["objects"]}
print("  备份里的原始坐标：")
for z in bak["map"]["zones"]:
    print("    %-6s %-8s %d 个" % (z["id"], z["name"], len(z["objects"])))

# 2) 写回：坐标用备份值，art 用当前值
for path, head in ((os.path.join(REPO, "js", "core", "levels.json"), None),
                   (os.path.join(REPO, "js", "core", "_data.js"), "App.levels = ")):
    if head is None:
        obj = json.load(io.open(path, encoding="utf-8"))
        raw = None
    else:
        t = io.open(path, encoding="utf-8").read()
        i = t.index(head) + len(head)
        a, b = span(t, t.index("{", i))
        obj = json.loads(t[a:b])
        raw = (t, a, b)

    n = 0
    for z in obj["map"]["zones"]:
        src = orig.get(z["id"], {})
        for o in z["objects"]:
            v = src.get(o["char"])
            if not v:
                print("    !! 备份缺 %s/%s" % (z["id"], o["char"]))
                continue
            o["x"], o["y"], o["r"] = int(v[0]), int(v[1]), int(v[2])
            n += 1
    if raw is None:
        io.open(path, "w", encoding="utf-8", newline="\n").write(
            json.dumps(obj, ensure_ascii=False, indent=1))
    else:
        t, a, b = raw
        out = t[:a] + json.dumps(obj, ensure_ascii=False,
                                 separators=(",", ":")) + t[b:]
        if len(out) < len(t) * 0.9:
            raise SystemExit("!! 新文件过小，拒绝写入")
        io.open(path, "w", encoding="utf-8", newline="\n").write(out)
    print("\n  已还原 %s（%d 个坐标；art 保留）" % (os.path.basename(path), n))

# 3) 自检：坐标必须落在 1800×1010 内，art 仍在
obj = json.load(io.open(os.path.join(REPO, "js", "core", "levels.json"), encoding="utf-8"))
print("\n  自检（viewBox 0 0 1800 1010）：")
bad = 0
for z in obj["map"]["zones"]:
    over = [o["char"] for o in z["objects"] if o["x"] > 1800 or o["y"] > 1010]
    bad += len(over)
    print("    %-6s %-8s %2d 个  越界=%s  art=%s"
          % (z["id"], z["name"], len(z["objects"]),
             "、".join(over) if over else "无", z.get("art")))
print("     越界合计 %d（应为 0）" % bad)
