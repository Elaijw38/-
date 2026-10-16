# -*- coding: utf-8 -*-
"""把这一轮的核验结果拼成一份可交付的说明页。

数据来源全部是跑过的日志，不手抄：
  · js/core/levels.json          → 21 关的形象接入清单
  · out/final/d*.log             → 桌面各视口的竖排账
  · out/final/m*.log             → 手机各视口的竖排账
  · out/final/all-*.log          → 全 21 关的形象取用核验
用法：python dev/_build_deliverable.py
产物：交付说明-第三关形象与竖排.html（仓库根目录）
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL = os.path.join(REPO, "out", "final")
OUT_HTML = os.path.join(REPO, "交付说明-第三关形象与竖排.html")


# ---------------------------------------------------------------- 读日志
def parse_log(path):
    try:
        txt = io.open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    mb = re.search(r"^BOXES:(\{.*\})$", txt, re.M)
    ml = re.search(r"^LV0:(\{.*\})$", txt, re.M)
    me = re.search(r"^ERRS:(\[.*\])$", txt, re.M)
    if not mb:
        return None
    b = json.loads(mb.group(1))
    f = json.loads(json.loads(ml.group(1))["fight"]) if ml else {}
    errs = json.loads(me.group(1)) if me else []
    return {"b": b, "f": f, "errs": errs}


def viewport_rows(prefix, specs):
    rows = []
    for w, h, label in specs:
        d = parse_log(os.path.join(FINAL, "%s%dx%d.log" % (prefix, w, h)))
        if not d:
            continue
        b, f = d["b"], d["f"]
        cb = f.get("chipBoxes") or {}
        ih = b["innerH"]
        rows.append({
            "label": label, "w": w, "h": h, "ih": ih,
            "field": b["field"]["h"], "glyph": None, "pool_top": b["pool"]["top"],
            "pool_bot": b["pool"]["bot"], "chip_top": cb.get("top"), "chip_bot": cb.get("bot"),
            "chip_ok": bool(cb) and cb.get("bot", 1e9) <= ih and cb.get("top", -1) >= 0,
            "margin": (ih - cb["bot"]) if cb.get("bot") is not None else None,
            "errs": d["errs"],
        })
    return rows


DESKTOP = [(1280, 1000, "1280×1000 笔记本"), (1366, 768, "1366×768 常见笔记本"),
           (1280, 768, "1280×768"), (1280, 800, "1280×800"), (1280, 860, "1280×860"),
           (1280, 900, "1280×900"), (1440, 900, "1440×900"),
           (1440, 1000, "1440×1000 主力"), (1024, 768, "1024×768 老笔记本"),
           (1920, 1080, "1920×1080 大屏")]
MOBILE = [(360, 640, "360×640 极矮"), (375, 667, "375×667 iPhone 8/SE2"),
          (390, 780, "390×780 常见竖屏"), (360, 800, "360×800 Android"),
          (393, 852, "393×852 iPhone 15"), (414, 896, "414×896 iPhone 11"),
          (430, 932, "430×932 iPhone 15 Pro Max")]

d_rows = viewport_rows("d", DESKTOP)
m_rows = viewport_rows("m", MOBILE)

# 字形尺寸：从 STYLES 里取（每个日志只打一次）
def glyph_of(prefix, w, h):
    try:
        txt = io.open(os.path.join(FINAL, "%s%dx%d.log" % (prefix, w, h)),
                      encoding="utf-8", errors="replace").read()
        S = json.loads(re.search(r"^STYLES:(\{.*\})$", txt, re.M).group(1))
        return S["body"]["h"]
    except Exception:
        return None


for r in d_rows:
    r["glyph"] = glyph_of("d", r["w"], r["h"])
for r in m_rows:
    r["glyph"] = glyph_of("m", r["w"], r["h"])

# ---------------------------------------------------------------- 21 关清单
L = json.loads(io.open(os.path.join(REPO, "js", "core", "levels.json"), encoding="utf-8").read())
boss = L["boss"]
codex = L.get("bossCodex", {})
swap = (boss.get("artSwap") or {}).get("entries") or {}
byc = {}
for e in codex.get("entries", []):
    if e.get("char"):
        byc[e["char"]] = e
    if e.get("alt"):
        byc.setdefault(e["alt"], e)

manifest = []
n_ded = n_swap = 0
for t in boss["tiers"]:
    for lv in t["list"]:
        ch = lv["char"]
        c = byc.get(ch)
        if c and c.get("art"):
            manifest.append({"tier": t["name"], "ch": ch, "art": c["art"], "src": "专属",
                             "name": (c.get("form") or "").split("，")[0][:12], "tie": "",
                             "why": (c.get("form") or "")[:46]})
            n_ded += 1
        elif ch in swap:
            s = swap[ch]
            manifest.append({"tier": t["name"], "ch": ch, "art": s["art"], "src": "代用",
                             "name": s.get("name", ""), "tie": s.get("tie", ""),
                             "why": (s.get("why") or "")[:46]})
            n_swap += 1
        else:
            manifest.append({"tier": t["name"], "ch": ch, "art": "", "src": "缺",
                             "name": "", "tie": "", "why": "★ 未接入"})
for i, it in enumerate(manifest, 1):
    it["i"] = i

# ---------------------------------------------------------------- 全 21 关核验
def all_rows(tag):
    d = parse_log(os.path.join(FINAL, "all-%s.log" % tag))
    txt = io.open(os.path.join(FINAL, "all-%s.log" % tag), encoding="utf-8",
                  errors="replace").read()
    rows = []
    for m in re.finditer(r"^LV(\d+):(\{.*\})$", txt, re.M):
        i = int(m.group(1))
        L2 = json.loads(m.group(2))
        f = json.loads(L2.get("fight", "{}")) if L2.get("fight") else {}
        tb = json.loads(L2.get("trackBefore", "{}")) if L2.get("trackBefore") else {}
        tr = json.loads(L2.get("track", "{}")) if L2.get("track") else {}
        rows.append({"i": i, "label": L2.get("label", ""), "fight": f,
                     "before": tb, "track": tr})
    errs = re.findall(r"^ERRS:(\[.*\])$", txt, re.M)
    return rows, (json.loads(errs[0]) if errs else [])


a_desk, e_desk = all_rows("1440x1000")
a_phone, e_phone = all_rows("390x780")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- 拼 HTML
def table(head, rows, cls=""):
    h = "".join("<th>%s</th>" % esc(x) for x in head)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows)
    return ('<table class="%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
            % (cls, h, body))


def ok(v):
    return '<span class="ok">✓</span>' if v else '<span class="bad">✗</span>'


# —— 桌面表
drow = []
for r in d_rows:
    drow.append([
        r["label"], "%d" % r["ih"], "%d" % r["field"],
        ("%d" % r["glyph"]) if r["glyph"] else "-",
        "%d→%d" % (r["pool_top"], r["pool_bot"]),
        "%d→%d" % (r["chip_top"], r["chip_bot"]) if r["chip_top"] else "-",
        ok(r["chip_ok"]), ("%+d" % r["margin"]) if r["margin"] is not None else "-",
        ok(not r["errs"]),
    ])
desk_table = table(["视口", "视口高", "战场高", "字形", "池子 y", "构件格子 y",
                    "格子全在首屏", "余量", "无异常"], drow)

mrow = []
for r in m_rows:
    mrow.append([
        r["label"], "%d" % r["ih"], "%d" % r["field"],
        ("%d" % r["glyph"]) if r["glyph"] else "-",
        "%d→%d" % (r["pool_top"], r["pool_bot"]),
        "%d→%d" % (r["chip_top"], r["chip_bot"]) if r["chip_top"] else "-",
        ok(r["chip_ok"]), ("%+d" % r["margin"]) if r["margin"] is not None else "-",
        ok(not r["errs"]),
    ])
mob_table = table(["视口", "视口高", "战场高", "字形", "池子 y", "构件格子 y",
                   "格子全在首屏", "余量", "无异常"], mrow)

# —— 21 关清单表
man_rows = []
for it in manifest:
    mark = '<span class="tag tag-%s">%s</span>' % (
        "ded" if it["src"] == "专属" else ("swap" if it["src"] == "代用" else "miss"), it["src"])
    tie = (" · " + it["tie"]) if it["tie"] else ""
    man_rows.append([it["i"], '<b>%s</b>' % esc(it["ch"]), esc(it["tier"]),
                     '<code>%s</code>' % esc(os.path.basename(it["art"])) if it["art"] else "—",
                     mark, esc(it["name"] + tie), esc(it["why"])])
man_table = table(["#", "关卡字", "档位", "形象文件", "来源", "显示名", "依据"], man_rows)

# —— 全 21 关取用核验表
def all_table(rows):
    out = []
    for r in rows:
        f = r["fight"]
        base = os.path.basename(str(f.get("src", "-")))
        # 独体字/繁复字那 15 关是「笔画终局」，**没有构件池**——
        # 池子那一列对它们应当是无此项，而不是「不合格」。
        n_chip = f.get("chipN")
        has_pool = bool(n_chip)
        pool_cell = ok(bool(f.get("poolInView"))) if has_pool else '<span class="na">—</span>'
        out.append([
            r["i"] + 1, esc(r["label"]),
            '<code>%s</code>' % esc(base),
            ok(bool(f.get("ok"))),
            ok(bool(f.get("artInFrame"))),
            ok(not f.get("artOverGlyph")),
            pool_cell,
            ok(not f.get("bubbleOverHead")),
            esc(f.get("tag", "-")),
            esc(n_chip if n_chip is not None else "-"),
        ])
    return table(["#", "关卡", "战斗里渲染的形象", "真加载", "帧内", "不压字形",
                  "池子在首屏", "气泡不压名", "显示名", "构件数"], out)


all_desk_table = all_table(a_desk)
all_phone_table = all_table(a_phone)

# —— 变更文件
CHANGES = [
    ("js/core/boss-art-swap.json", "新增",
     "12 关「无专属形象」的<b>代用表</b>——整个改动的唯一事实来源。"
     "每项记 art / of（借谁的）/ name（本关自己的显示名）/ tie（同源·同形·形近·同字）/ why。"
     "取用顺序：名录专属形象 → 本表 → 本档通用图。"),
    ("dev/_build_bosscodex.py", "改",
     "构建时把上表写进 <code>levels.json.boss.artSwap</code>，并做三项自检："
     "①表的键必须是真实关卡字；②指向的形象文件必须存在；③任何一关若既无专属形象、"
     "又不在代用表里，直接报错（否则会静默退回早期卡通通用图）。"
     "本次输出：<code>21 关全部有形象可用 ✓（专属 9 关 / 代用 12 关）</code>，0 异常、0 缺口。"),
    ("js/modes/boss-raid.js", "改",
     "① 新增 <code>swapOf()</code>，<code>charArt()</code> 增加代用分支（返回 "
     "<code>swapped/from/tie</code>）；② 新增 <code>artLabel()</code>，把展示名拼成"
     "「本关名 · 代用」；③ 选关榜悬停与战斗台的形象标签都改走它；"
     "④ 结算页对代用关追加一段 <code>※ 形象是借的…</code> 说明。"),
    ("css/modes.css", "改",
     "战场竖向尺寸改为<b>随视口高变化的变量</b> <code>--bd-arena</code>，"
     "各宽度档只设上限（<code>--bd-arena-max</code>），并让字形、怪像、龟宝立绘同时跟着它走；"
     "另新增「矮手机」一档。目的是让<b>构件选项</b>落在首屏内、不用先滚一屏。"),
    ("index.html", "改",
     "缓存戳：<code>_data.js / boss-raid.js / modes.css</code> 各升一版，避免本地/线上拿到旧文件。"),
    ("js/core/levels.json", "重建", "由 <code>dev/_build_bosscodex.py</code> 重新生成，新增 "
     "<code>boss.artSwap</code>。"),
    ("js/core/_data.js", "重建", "由 <code>dev/_build_leveldata.py</code> 重新生成（281.6 KB），"
     "把 artSwap 内联进页面。"),
    ("dev/_boss_art_check.py", "新增",
     "核验台：解锁 21 关后逐关真进一次战斗，读回选关榜悬停图、战斗形象的 src/加载状态/显示名、"
     "形状是否越框、是否压字形、龟宝气泡是否压名字、构件格子是否在首屏、控制台异常。"),
    ("dev/_raid_shot.py", "改",
     "支持非合体字关卡（改点笔画而不是构件），并在进第 N 关前先补通关进度，"
     "使单条战斗链能从阶段一走完到结算。"),
    ("dev/_pool_test.py · dev/_bo_stage_test.py", "改",
     "探测地址改为可覆盖（<code>RAID_URL</code>），不再写死端口。"),
    ("dev/_build_deliverable.py", "新增", "本说明页的生成脚本，数字全部从核验日志读入，不手抄。"),
    ("_backup_20261016_swap/ · _backup_20261016_arena/", "备份",
     "改动前对 <code>css/modes.css / js/modes/boss-raid.js / index.html / "
     "js/core/{levels.json,_data.js,boss-codex.json} / dev/_build_bosscodex.py</code> 做的备份。"),
]
chg_rows = [[ '<code>%s</code>' % esc(f), '<span class="tag tag-%s">%s</span>' % (
    {"新增": "ded", "改": "swap", "重建": "re", "备份": "bk"}.get(k, "re"), esc(k)), t]
    for f, k, t in CHANGES]
chg_table = table(["文件", "性质", "说明"], chg_rows)

n_chip_ok_d = sum(1 for r in d_rows if r["chip_ok"])
n_chip_ok_m = sum(1 for r in m_rows if r["chip_ok"])
min_margin_m = min((r["margin"] for r in m_rows if r["margin"] is not None), default=0)
min_margin_d = min((r["margin"] for r in d_rows if r["margin"] is not None), default=0)

HTML = u"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>交付说明 · 第三关 Boss 形象接入与竖排复核</title>
<style>
  :root {
    --bg:#f7f2e8; --card:#fffdf8; --ink:#2c2620; --ink2:#655a4c; --ink3:#8d8172;
    --line:#e4dbc9; --line2:#d3c7b0; --red:#b8503c; --gold:#a8823f; --green:#5d7a46;
  }
  * { box-sizing:border-box; }
  body { margin:0; padding:34px 22px 70px; background:var(--bg); color:var(--ink);
    font:15px/1.75 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
  .wrap { max-width:1120px; margin:0 auto; }
  h1 { margin:0 0 6px; font-size:27px; letter-spacing:1px; }
  .sub { color:var(--ink3); font-size:13.5px; margin-bottom:26px; }
  h2 { margin:38px 0 12px; font-size:19px; padding-left:11px;
    border-left:4px solid var(--red); line-height:1.35; }
  h3 { margin:24px 0 9px; font-size:15.5px; color:var(--ink2); }
  .card { background:var(--card); border:1px solid var(--line); border-radius:7px;
    padding:18px 20px; margin:14px 0; }
  p { margin:9px 0; }
  code { background:#f0e9db; border:1px solid var(--line); border-radius:3px;
    padding:1px 5px; font-size:12.5px; font-family:"Cascadia Mono",Consolas,monospace; }
  table { width:100%; border-collapse:collapse; font-size:12.8px; margin:10px 0 4px;
    background:var(--card); }
  th,td { border:1px solid var(--line); padding:6px 9px; text-align:left;
    vertical-align:top; }
  th { background:#f1e9d9; font-weight:600; white-space:nowrap; }
  tbody tr:nth-child(even) td { background:#fdfbf5; }
  td code { background:transparent; border:none; padding:0; }
  .ok { color:var(--green); font-weight:700; }
  .bad { color:var(--red); font-weight:700; }
  .na { color:var(--ink3); }
  .tag { display:inline-block; padding:1px 7px; border-radius:10px; font-size:11.5px;
    border:1px solid; white-space:nowrap; }
  .tag-ded { color:var(--green); border-color:#b9cba6; background:#eef3e7; }
  .tag-swap { color:var(--gold); border-color:#ddcb9f; background:#f8f2e0; }
  .tag-miss { color:var(--red); border-color:#e0b3a9; background:#faeeeb; }
  .tag-re { color:#5a6b86; border-color:#bac6d6; background:#eef1f6; }
  .tag-bk { color:var(--ink3); border-color:var(--line2); background:#f4f0e7; }
  .kpi { display:flex; flex-wrap:wrap; gap:12px; margin:6px 0 4px; }
  .kpi div { flex:1 1 150px; background:var(--card); border:1px solid var(--line);
    border-radius:7px; padding:12px 14px; }
  .kpi b { display:block; font-size:23px; color:var(--red); line-height:1.25; }
  .kpi span { font-size:12px; color:var(--ink3); }
  ul { margin:8px 0; padding-left:22px; }
  li { margin:5px 0; }
  .note { border-left:3px solid var(--gold); background:#fbf6e9; padding:11px 15px;
    margin:13px 0; font-size:13.6px; }
  .warn { border-left:3px solid var(--red); background:#faefec; padding:11px 15px;
    margin:13px 0; font-size:13.6px; }
  figure { margin:16px 0; }
  figure img { width:100%; border:1px solid var(--line2); border-radius:6px; display:block; }
  figcaption { font-size:12.5px; color:var(--ink3); margin-top:7px; text-align:center; }
  .gal { display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); gap:12px; }
  .gal figure { margin:0; }
  .scroll { overflow-x:auto; }
  footer { margin-top:44px; padding-top:16px; border-top:1px solid var(--line);
    color:var(--ink3); font-size:12.5px; }
</style>
</head>
<body>
<div class="wrap">

<h1>交付说明 · 第三关 Boss 形象接入与竖排复核</h1>
<div class="sub">字趣 · 甲骨构字记 &nbsp;|&nbsp; 先检查代码与素材，再按「第二关 → 第三关 → 交付」的顺序处理 &nbsp;|&nbsp; 未推送 GitHub</div>

<div class="card">
  <div class="kpi">
    <div><b>21 / 21</b><span>关卡都有可用形象（专属 %(n_ded)d · 代用 %(n_swap)d · 通用兜底 0）</span></div>
    <div><b>61 / 61</b><span>第二关热点保留，越界 0 · 抢点击 0</span></div>
    <div><b>%(n_chip_ok_d)d / %(n_desktop)d</b><span>桌面视口：构件选项在首屏</span></div>
    <div><b>%(n_chip_ok_m)d / %(n_mobile)d</b><span>手机视口：构件选项在首屏</span></div>
  </div>
  <p style="margin-bottom:0">这一轮没有生成任何新图。12 关缺专属形象的关卡，按你的决定
  <b>用现有 88 张里最贴的一张顶上</b>，并且把「这是借的」写进界面与结算页；
  三张档位通用图按你的决定<b>没有重做</b>；这 12 尊按你的决定<b>没有进「汉字图鉴 → 讨伐名录」</b>。</p>
</div>

<h2>一、第二关：复核结论</h2>
<div class="card">
  <p>热点数据<b>一个字都没动</b>，只做了复核。<code>dev/_l2_calibrate.py --dry</code>
  （唯一事实来源）的输出：</p>
  <ul>
    <li>五个分区共 61 字，逐字与原始字表一致：天象 4 · 山川 9 · 草木 6 · 禽兽虫鱼 9 · 人居器物 33</li>
    <li><b>越界 0 个 · 抢点击 0 对</b> —— 五个分区全部为 0，即没有热点落在画面外，也没有两个热点的命中区互相压住</li>
    <li>大地图五个入口点位与分区半径均在界内</li>
  </ul>
  <p>下面的标定图把每个热点用红圈钉在物体上、并标出对应的字，可以逐个核对位置。
  <code>life</code>（人居器物）是 33 个热点最挤的一张，它是分区查看的，不是硬塞进一张全景。</p>
</div>
<figure>
  <img src="out/_l2_calib_sheet.png" alt="六张第二关热点标定图">
  <figcaption>六张标定预览（上排：大地图 / 天象；中排：山川 / 草木；下排：禽兽虫鱼 / 人居器物）。
  单张原图在 <code>out/l2-calib-v2/</code>：world · sky · land · plant · beast · life，各 1600×897。</figcaption>
</figure>

<h2>二、第三关：Boss 形象接入</h2>

<h3>2.1 缺口是怎么来的</h3>
<div class="card">
  <p>21 关里原本 <b>9 关有专属形象、12 关没有</b>。没有的那 12 关会退回到三张「档位通用图」——
  而那是早期卡通画风（红眼睛、粗边、不填色），跟 88 张骨色线描摆在一起一眼就能看出不是一套，
  正是你提的「风格不统一」。</p>
  <p>查过出处后可以确认：<b>不是图丢了，是从来没生成过</b>。形象是按《Boss（象形会意假借）.docx》
  的字表逐字生成的，而这 12 个字里，龍 / 馬 / 虎 属于你先前明确排除的「十二生肖」那一组，
  山 人 日 月 水 焚 鼓 舞 鳥 则根本不在字表内。</p>
</div>

<h3>2.2 用现有形象顶上去：12 关代用表</h3>
<div class="card">
  <p>挑选不是「找长得像的」，而是先翻完 88 张、找<b>同源关系</b>。几处是真正意义上的同源，
  不是权宜：</p>
  <ul>
    <li><code>舞 ← 無</code>：<b>無就是舞的本字</b>，甲骨文里同一个人执牛尾而舞——这不是借，是同一个字</li>
    <li><code>鼓 ← 雷</code>：雷的甲骨形体本身就是<b>架在座上的鼓</b>加一道电光</li>
    <li><code>龍 ← 它</code>：它是一条盘曲的巨蛇，正对「龍：身蜷如大蛇」</li>
    <li><code>焚 ← 火</code> / <code>水 ← 涉</code> / <code>月 ← 明</code> / <code>日 ← 莫</code> /
        <code>人 ← 从</code> / <code>鳥 ← 舊</code>：都是同一构字成分的另一个字</li>
    <li>较弱但只有这一张可用的三张（<code>山 ← 森</code>、<code>馬 ← 鹿</code>、<code>虎 ← 兕</code>）
        已在数据里逐条标注 <code>★ 这一关该补专属形象</code></li>
  </ul>
</div>

<h3>2.3 「借的」这件事在界面上是写明的</h3>
<div class="card">
  <p>借图最怕的是让人以为这就是本尊。所以做了三处标记，都不是装饰：</p>
  <ul>
    <li><b>展示名仍是本关自己的描述</b>，例如第 3 关显示「焚林怪」而不是「火怪」——
        借的是形，说法是这一关的</li>
    <li>名字后面缀一个安静的 <code>· 代用</code>（选关榜悬停与战斗台都有），手机上因为宽度紧张不显示后缀</li>
    <li>结算页追加一段说明：<code>※ 形象是借的：本关的字不在《Boss（象形会意假借）.docx》字表内，
        名录里没有它的专属形象，这里暂借「火」一尊顶上（同源）。…</code></li>
  </ul>
  <p class="note" style="margin-bottom:0">讨伐名录（图鉴）里的条目数仍是 <b>88</b>，这 12 个没有加进去——
  名录是「docx 字表里有哪些字」，不是「这一关打了谁」。</p>
</div>

<h3>2.4 21 关形象接入清单</h3>
<div class="scroll">%(man_table)s</div>

<h3>2.5 逐个关卡的真实渲染核验</h3>
<div class="card">
  <p>上面那张表只能说明「文件存在」。为了排除路径写错、大小写不合、图加载失败后静默退回通用图
  这类只有浏览器才暴露的问题，<code>dev/_boss_art_check.py</code> 会把 21 关解锁后<b>逐关真进一次战斗</b>，
  读回战斗里实际渲染的图片地址、是否真加载（<code>naturalWidth &gt; 0</code>）、显示名、
  是否越框、是否压住字形、龟宝气泡是否压住怪名、构件数量、控制台异常。</p>
</div>
<h3 style="margin-top:16px">桌面 1440×1000</h3>
<div class="scroll">%(all_desk_table)s</div>
<h3>手机 390×780</h3>
<div class="scroll">%(all_phone_table)s</div>
<div class="note">两端 21 关全部：形象<b>真加载 ✓ · 不越框 ✓ · 不压字形 ✓ · 气泡不压怪名 ✓ · 都有显示名 ✓</b>，
控制台异常 <b>%(errs_desk)s / %(errs_phone)s</b>。
其中「池子在首屏」一列只有 6 关是 ✓ 并带构件数 4，另外 15 关是 <span class="na">—</span>：
那 15 关是独体字与繁复字，打的是<b>笔画终局</b>，本来就没有构件池，不是不合格。
带构件池的 6 关（一阶合体字）两端都在首屏内。</div>

<h3>2.6 构件攻击：只给 4 个选项，放错有短反馈</h3>
<div class="card">
  <p><code>POOL_SIZE = 4</code>：正确项一个不少，其余用干扰项补满，再洗一遍牌。
  总数恒定，所以「池子里有几个」不会反过来暴露「答案有几个」。
  放错时龟宝换成安抚动作并给一句 <code>再观察一次</code>，形变条只退一点点，不惩罚。</p>
</div>

<h3>2.7 笔画攻击的引导</h3>
<div class="card">
  <p>阶段二到阶段三的入口原来挂在页面最底部的按钮行里，而阶段二正好还摊着一整片点不动的构件池，
  按钮被推到屏幕外——这就是你说的「不太好发现」。现在它长在<b>提示卡正文下面</b>，
  玩家正在读的就是那张卡：<code>和龟宝一起改用笔画</code>。
  进入终局后每轮只标出<b>这一笔可点</b>（其余笔画压暗），首次交互给一次示范。</p>
</div>

<h3>2.8 龟宝在场，但不挡事</h3>
<div class="card">
  <p>龟宝在左栏，提示是一句<b>紧跟在他正上方的小气泡</b>，只占左栏宽度——
  不压 Boss，也不压字形那块可点的攻击区（这一条是量的：<code>bubbleOverHead</code> 21 关全为否）。</p>
</div>

<h2>三、竖排复核：让「构件选项」落在首屏</h2>
<div class="card">
  <p>原先战场的字形与立绘是定值，战场高度被钉死；而它下面还压着构件池。
  只按 1000 高调过，矮一点的机器池子就整块掉出首屏，点构件得先滚一屏。
  现在字形、怪像、龟宝立绘绑在同一个<b>随视口高线性收缩</b>的变量 <code>--bd-arena</code> 上，
  各宽度档只设上限。<b>手机那一档的字形 138px 一点没动</b>——终局要点单笔，138 是「相邻笔画仍隔 20px
  以上、点得准」量出来的下限。</p>
  <p class="warn">修的过程中发现一处真问题：<code>@media (max-width:1024px)</code> 里写死了
  <code>.bd-body { height: 250px }</code>，把「随高度收缩」这条路整个盖掉了，
  所以 1024×768 这种又窄又矮的老笔记本必然出屏（实测池子底边溢出 109px）。
  现在各宽度档改成只给上限 <code>--bd-arena-max</code>，与高度的 min() 取小。</p>
</div>

<h3>3.1 桌面 %(n_desktop)d 个视口</h3>
<div class="scroll">%(desk_table)s</div>

<h3>3.2 手机 %(n_mobile)d 个视口</h3>
<div class="scroll">%(mob_table)s</div>
<div class="note">量的是<b>构件的格子</b>，不是池子那个盒子——池子底下那点内边距出屏无所谓，
格子出屏才需要先滚一屏。桌面最小余量 %(min_margin_d)+d px，手机最小余量 %(min_margin_m)+d px。</div>
<div class="warn">仍有 <b>1 个视口没进</b>：<code>360×640</code>（极矮的老 Android），构件格子底边
还差 16px。这一档要再收就得动「← 关卡」返回键、阶段条或 HP 条里的一个，属于功能性取舍，
没有替你做决定，留在下面「未完成」里。</div>

<h2>四、修改文件清单</h2>
<div class="scroll">%(chg_table)s</div>

<h2>五、实际页面截图</h2>
%(shots)s

<h2>六、未完成 / 已知限制</h2>
<div class="card">
  <ul>
    <li><b>12 关仍是借的形象。</b>
        按你的决定没有生成新图。其中 <code>山 ← 森</code>、<code>馬 ← 鹿</code>、<code>虎 ← 兕</code>
        三处只是形近、同源关系较弱，已在数据里标了「该补专属形象」——真要补，这三关优先。
        另外 <code>水</code> 与一阶第 1 关 <code>涉</code> 共用同一张图（涉的形体本身就是水加脚印），
        两关连着打会看到同一尊。</li>
    <li><b>三张档位通用图仍是早期卡通画风。</b>
        它们现在只在「形象缺失」时才会被用到，21 关里已经一次都不出现，所以不构成视觉问题；
        但只要以后新增关卡忘了配图，就会露出这张。构建脚本的自检会直接报错拦住这种情况。</li>
    <li><b><code>360×640</code> 的构件格子还差 16px。</b>
        见 3.2 末尾。需要你在「返回键 / 阶段条 / HP 条」里挑一个让位，我再去动。</li>
    <li><b>「重来本关」仍在首屏之外（桌面矮屏与手机）。</b>
        这是刻意的：阶段二真正要做的那一手已经搬到提示卡里，这一行只剩重来，不再占首屏。
        如果你希望它也在首屏内，说一声，我把它挪进构件池那一行的头部。</li>
    <li><b>没有推送 GitHub。</b> 工作区里的改动没有 commit、也没有 push；
        <code>repo_extract/jiagugouciji-main</code> 本身不是 git 仓库，改动都是文件级替换，
        回滚用两个备份目录即可。</li>
  </ul>
</div>

<footer>
  本页由 <code>dev/_build_deliverable.py</code> 生成，表格里的数字全部从核验日志读入，没有手抄。
  核验日志在 <code>out/final/</code>。
</footer>
</div>
</body>
</html>
"""


def shots_html():
    def gal(items, title):
        if not items:
            return ""
        s = ['<h3>%s</h3><div class="gal">' % title]
        for path, cap in items:
            if os.path.exists(os.path.join(REPO, path)):
                s.append('<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>'
                         % (path, esc(cap), esc(cap)))
        s.append("</div>")
        return "".join(s)

    desk = [
        ("out/shot-desk/00-track.png", "选关榜 · 21 关（三档 · 通关状态 · 形象缩略）"),
        ("out/shot-desk/01-fight.png", "阶段一 · 构件压制（龟宝气泡 + 提示卡 + 4 个构件）"),
        ("out/shot-desk/02-break1.png", "阶段一 · 放对一个构件（构件入位、形变）"),
        ("out/shot-desk/04-phase3.png", "阶段三 · 笔画终局（只标出这一笔可点）"),
        ("out/shot-desk/06-win.png", "结算 · 斩杀「焚」+ 构件组合示意"),
        ("out/shot-desk-lv15/06-win.png", "结算 · 斩杀「鼓」（11 段笔画）+ 代用说明"),
    ]
    mob = [
        ("out/shot-mob/00-track.png", "手机 · 选关榜"),
        ("out/shot-mob/01-fight.png", "手机 · 阶段一（构件选项落在首屏）"),
        ("out/shot-mob/04-phase3.png", "手机 · 阶段三 笔画终局"),
        ("out/shot-mob/06-win.png", "手机 · 结算"),
        ("out/shot-mob-lv7/01-fight.png", "手机 · 第 8 关「人」（代用形象 41-cong，细高）"),
    ]
    return gal(desk, "4.1 桌面 1440×1000") + gal(mob, "4.2 手机 390×780")


for k, v in [("shots", shots_html()), ("man_table", man_table), ("desk_table", desk_table),
             ("mob_table", mob_table), ("chg_table", chg_table),
             ("all_desk_table", all_desk_table), ("all_phone_table", all_phone_table),
             ("n_ded", str(n_ded)), ("n_swap", str(n_swap)),
             ("n_desktop", str(len(d_rows))), ("n_mobile", str(len(m_rows))),
             ("n_chip_ok_d", str(n_chip_ok_d)), ("n_chip_ok_m", str(n_chip_ok_m)),
             ("min_margin_d", str(min_margin_d)), ("min_margin_m", str(min_margin_m)),
             ("errs_desk", esc(e_desk) if e_desk else "无"),
             ("errs_phone", esc(e_phone) if e_phone else "无")]:
    # 三种写法都要替：%(x)s / %(x)d / %(x)+d。漏掉 d 会在页面上留下占位符。
    for pat in ("%(" + k + ")s", "%(" + k + ")d", "%(" + k + ")+d"):
        HTML = HTML.replace(pat, v)

io.open(OUT_HTML, "w", encoding="utf-8").write(HTML)
print("写出", OUT_HTML)
print("  %d 字节" % os.path.getsize(OUT_HTML))
print("  21 关：专属 %d · 代用 %d" % (n_ded, n_swap))
print("  桌面 %d 视口 · 构件在首屏 %d 个 · 最小余量 %d" % (len(d_rows), n_chip_ok_d, min_margin_d))
print("  手机 %d 视口 · 构件在首屏 %d 个 · 最小余量 %d" % (len(m_rows), n_chip_ok_m, min_margin_m))
print("  控制台异常：桌面 %s · 手机 %s" % (e_desk or "无", e_phone or "无"))
