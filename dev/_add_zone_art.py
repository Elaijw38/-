# -*- coding: utf-8 -*-
"""给 _data.js 的五个 zone 各加一个 art 字段，指向该分区的场景原画。

为什么改数据而不是在渲染处写死一个数组：
  渲染层原来把 assets/wangyi-atlas.svg（**大地图底图**）当小地图插画用，
  五幅小地图长得一模一样。分区与插画的对应关系属于**内容**，
  放在数据里，以后换主题只改这一处；写死在 JS 里就得跟着改代码。

踩过的坑（很重要）：
  第一版用 `t.index(";\\n", i)` 找 JSON 结尾——**会在字符串内容里提前命中**
  （_note 字段里就含 "; "），结果把文件截成 7457 字符、写坏了。
  正确做法是**扫大括号配平**找到真正的结尾（字符串内的括号要跳过）。

用法：python dev/_add_zone_art.py    可重复执行（已有 art 就跳过）
"""
import io
import json
import os

P = r"C:\DSH\字趣\js\core\_data.js"

ART = {
    "sky":   "out/minimaps/minimap-01-天象.jpg",
    "land":  "out/minimaps/minimap-02-山川.jpg",
    "plant": "out/minimaps/minimap-03-草木.jpg",
    "beast": "out/minimaps/minimap-04-禽兽文鱼.jpg",
    "life":  "out/minimaps/minimap-05-人居器物.jpg",
}
# 注意：上面 beast 的写法必须与磁盘上的真实文件名一致，下面会核对。
ART["beast"] = "out/minimaps/minimap-04-禽兽虫鱼.jpg"

HEAD = "App.levels = "


def json_span(text, start):
    """从 start 处的 '{' 起扫大括号配平，返回 JSON 片段的 [起, 止) 。
    必须跳过字符串内部（含转义），否则会被内容里的括号带偏。"""
    assert text[start] == "{", "起点不是 {"
    depth = 0
    i = start
    in_str = False
    esc = False
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1
        i += 1
    raise SystemExit("!! 大括号不配平，文件可能已损坏")


t = io.open(P, encoding="utf-8").read()
i = t.index(HEAD)
obj_start = t.index("{", i + len(HEAD))
a, b = json_span(t, obj_start)
data = json.loads(t[obj_start:b])
print("  解析成功：原文件 %d 字符，JSON 片段 %d 字符" % (len(t), b - a))

zones = data["map"]["zones"]
changed = 0
for z in zones:
    art = ART.get(z["id"])
    if not art:
        print("  !! 未知 zone id：%s" % z["id"])
        continue
    if z.get("art") == art:
        print("  = %-6s 已有 art" % z["id"])
        continue
    new = {}
    for k, v in z.items():
        new[k] = v
        if k == "name":
            new["art"] = art
    new.setdefault("art", art)
    z.clear()
    z.update(new)
    changed += 1
    print("  + %-6s %-8s -> %s" % (z["id"], z["name"], art))

if not changed:
    print("\n  无需改动")
else:
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    out = t[:obj_start] + body + t[b:]
    # 写前自检：新文件必须也能解析，且不能比原文件小太多
    if len(out) < len(t) * 0.9:
        raise SystemExit("!! 新文件比原文件小太多（%d vs %d），拒绝写入"
                         % (len(out), len(t)))
    ni = out.index(HEAD) + len(HEAD)
    na, nb = json_span(out, out.index("{", ni))
    chk = json.loads(out[na:nb])
    if len(chk["map"]["zones"]) != 5 or len(chk["map"]["zones"][0]["objects"]) < 1:
        raise SystemExit("!! 自检失败：zone 数或 objects 异常，拒绝写入")
    io.open(P, "w", encoding="utf-8", newline="\n").write(out)
    print("\n  已写回 %s（改 %d 个 zone，%d → %d 字符）" % (P, changed, len(t), len(out)))

print("\n  校验：")
ok = True
for z in data["map"]["zones"]:
    rel = z.get("art", "")
    ex = os.path.exists(os.path.join(r"C:\DSH\字趣", rel))
    if not ex:
        ok = False
    print("    %-6s %-8s %-44s %s" % (z["id"], z["name"], rel or "(无)",
                                      "存在" if ex else "缺失 X"))
print("  结论：%s" % ("五个分区都有可用插画" if ok else "有缺失，需检查"))
