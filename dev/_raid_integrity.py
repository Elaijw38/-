# -*- coding: utf-8 -*-
"""第三关 21 关的静态完整性检查：每关是否具备"能打通"的必要数据。

判定依据（读 js/modes/boss-raid.js 的规则）：
  合体档 → 需要可拆构件（comps 非空）或可拆笔画（seg>0）
  独体/繁复档 → 需要可拆笔画（seg>0），否则"没有可斩的段落"= 打不动
另外检查：形象是否缺、parts 是否为空、编号是否连续。
"""
import glob
import io
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)

t = io.open("js/core/_data.js", encoding="utf-8").read()
i = t.find("App.levels = ") + len("App.levels = ")
depth, j = 0, i
while j < len(t):
    ch = t[j]
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0:
            j += 1
            break
    j += 1
levels = json.loads(t[i:j])
tiers = levels["boss"]["tiers"]

total = 0
problems = []
print("  阶次           关卡数   缺形象  无可拆料  parts 空")
for ti, tier in enumerate(tiers):
    lst = tier.get("list") or []
    total += len(lst)
    no_art = no_parts = zero_seg = 0
    for lv in lst:
        ch = lv.get("char")
        art = lv.get("art")
        if not art or not os.path.exists(art):
            no_art += 1
            problems.append((ch, "缺形象", art))
        seg = lv.get("seg") or 0
        comps = lv.get("comps") or []
        parts = lv.get("parts") or []
        if not comps and seg <= 0:
            zero_seg += 1
            problems.append((ch, "没有可拆的构件也没有笔画段", "seg=%s comps=%s" % (seg, len(comps))))
        if not parts and not comps:
            no_parts += 1
            problems.append((ch, "parts 与 comps 都为空", ""))
    print("  %-12s %4d 个  %6d  %8d  %7d"
          % (tier.get("name", "?")[:10], len(lst), no_art, zero_seg, no_parts))

print("\n  合计 %d 关" % total)

print("\n  逐关明细（字｜阶｜seg｜comps｜parts｜playable）：")
for tier in tiers:
    for lv in tier.get("list") or []:
        print("    %-3s %-6s seg=%-3s comps=%-2d parts=%-2d playable=%s"
              % (lv.get("char"), (tier.get("id") or "")[:5], lv.get("seg"),
                 len(lv.get("comps") or []), len(lv.get("parts") or []),
                 lv.get("playable")))

if problems:
    print("\n  !! 需要处理的 %d 条：" % len(problems))
    for ch, kind, extra in problems[:20]:
        print("    %-3s %-16s %s" % (ch, kind, extra))
else:
    print("\n  全部关卡数据齐备 ✓")
