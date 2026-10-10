# -*- coding: utf-8 -*-
"""生成「手绘实物 vs 真实甲骨字形」试样页，并截图。

与 openmaic 卡片不同，这里直接读项目里的 glyph-parts.json，
把【真实甲骨字形】内联进来，所以看到的是最终会出现在地图上的效果。
"""
import io, json, os, subprocess, tempfile, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _glyphdata import build_svg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
GL = os.path.join(ROOT, "js", "core", "glyph-parts.json")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(ROOT, "_check")
os.makedirs(OUT, exist_ok=True)

gl = json.loads(io.open(GL, encoding="utf-8").read())
parts = gl["parts"]
CANVAS = gl.get("canvas", 100)


def glyph_inner(ch):
    p = parts.get(ch)
    if not p:
        return None
    # {C} 是描边占位；这里整张 SVG 用 currentColor，直接去掉占位
    return build_svg(p, "currentColor")


def glyph_svg(ch, cls):
    inner = glyph_inner(ch)
    if inner is None:
        return '<div class="missing">缺字形</div>'
    return ('<svg class="%s" viewBox="0 0 %d %d" fill="none" '
            'stroke="currentColor" stroke-width="3.2" stroke-linecap="round" '
            'stroke-linejoin="round">%s</svg>' % (cls, CANVAS, CANVAS, inner))


# 我手绘的实物图（线描，笔法与地图一致）
DRAW = {
    "山": '<path d="M6 80 L30 44 L42 60 L58 28 L80 80 Z"/>'
          '<path d="M50 44 L57 37"/><path d="M20 88 h62" stroke-width="2.2" opacity=".5"/>',
    "水": '<path d="M50 14 C34 30 26 44 26 56 C26 72 36 84 50 84 '
          'C64 84 74 72 74 56 C74 44 66 30 50 14 Z"/>'
          '<path d="M34 44 h12" stroke-width="2.6" opacity=".6"/>'
          '<path d="M56 52 h12" stroke-width="2.6" opacity=".6"/>',
    "木": '<path d="M50 86 V40"/>'
          '<path d="M50 54 C26 52 18 34 22 18 C34 14 48 26 50 40"/>'
          '<path d="M50 60 C74 58 82 40 78 24 C66 20 52 32 50 46"/>'
          '<path d="M36 86 h28" stroke-width="2.4" opacity=".55"/>',
    "日": '<circle cx="50" cy="50" r="30"/>'
          '<circle cx="50" cy="50" r="4.5" fill="currentColor" stroke="none"/>',
    "月": '<path d="M62 14 C40 24 30 38 30 52 C30 70 42 82 62 86 '
          'C48 76 42 64 42 50 C42 36 48 24 62 14 Z"/>'
          '<path d="M52 34 V66" stroke-width="2.6" opacity=".6"/>',
    "牛": '<path d="M22 26 C24 46 32 60 50 62 C68 60 76 46 78 26"/>'
          '<path d="M22 26 C14 22 10 14 12 6"/>'
          '<path d="M78 26 C86 22 90 14 88 6"/>'
          '<path d="M38 68 V86 M62 68 V86" stroke-width="2.8"/>',
    "羊": '<path d="M26 30 C20 18 30 8 40 14"/>'
          '<path d="M74 30 C80 18 70 8 60 14"/>'
          '<path d="M26 30 C28 50 38 62 50 62 C62 62 72 50 74 30"/>'
          '<path d="M40 68 V86 M60 68 V86" stroke-width="2.8"/>',
    "鱼": '<path d="M30 18 C52 20 76 40 78 50 C76 60 52 80 30 82 '
          'C24 60 24 40 30 18 Z"/>'
          '<path d="M78 50 L92 34 V66 Z"/>'
          '<circle cx="42" cy="44" r="3.4" fill="currentColor" stroke="none"/>',
    "鼎": '<path d="M28 16 h44"/><path d="M24 30 h52"/>'
          '<path d="M32 16 C30 34 26 50 24 62"/>'
          '<path d="M68 16 C70 34 74 50 76 62"/>'
          '<path d="M24 62 C38 72 62 72 76 62"/>'
          '<path d="M42 70 V86 M50 72 V88 M58 70 V86"/>',
    "舟": '<path d="M12 52 C30 74 70 74 88 52"/>'
          '<path d="M12 52 C30 66 70 66 88 52" stroke-width="2.2" opacity=".5"/>'
          '<path d="M50 34 V58"/><path d="M50 34 L74 26" stroke-width="2.6"/>',
    "宀": '<path d="M14 46 L50 16 L86 46"/>'
          '<path d="M22 46 V84 h56 V46"/>'
          '<path d="M42 84 V62 h16 v22"/>',
    "目": '<path d="M16 50 C30 28 70 28 84 50 C70 72 30 72 16 50 Z"/>'
          '<circle cx="50" cy="50" r="12"/>'
          '<circle cx="50" cy="50" r="3.6" fill="currentColor" stroke="none"/>',
    "戈": '<path d="M22 84 L22 14"/>'
          '<path d="M22 22 C40 14 60 16 74 26 C58 30 40 30 22 34 Z"/>'
          '<path d="M22 52 L44 62" stroke-width="2.8"/>',
    "贝": '<path d="M50 12 C34 24 26 40 26 54 C26 72 36 86 50 86 '
          'C64 86 74 72 74 54 C74 40 66 24 50 12 Z"/>'
          '<path d="M50 24 V80" stroke-width="2.4" opacity=".6"/>'
          '<path d="M38 44 h24" stroke-width="2.4" opacity=".6"/>',
}

CARDS = list(DRAW.keys())

cells = []
for ch in CARDS:
    p = parts.get(ch)
    mean = (p or {}).get("sourceChar") or ""
    note = ""
    if p and p.get("isFallback"):
        note = '<span class="fb">代用件</span>'
    cells.append(
        '<div class="cell">'
        '  <div class="pair">'
        '    <div class="side"><span class="lab">手绘实物</span>'
        '      <svg class="draw" viewBox="0 0 100 100" fill="none" stroke="currentColor" '
        'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">%s</svg></div>'
        '    <span class="arrow">→</span>'
        '    <div class="side"><span class="lab">甲骨字形</span>%s</div>'
        '  </div>'
        '  <div class="nm">%s %s</div>'
        '</div>' % (DRAW[ch], glyph_svg(ch, "orac"), ch, note))

HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>试样：手绘实物 vs 真实甲骨字形</title><style>
body { margin:0; padding:22px 24px 26px; background:#f4ecdc; color:#2a2118;
       font-family: "Songti SC","Noto Serif SC",SimSun,serif; }
h1 { font-size:19px; margin:0 0 6px; letter-spacing:1px; }
p.lead { font-size:13px; color:#5a4c38; line-height:1.75; margin:0 0 16px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(258px,1fr)); gap:11px; }
.cell { background:#f9f2e2; border:1px solid #c8ab7c; border-radius:9px;
        padding:9px 10px 8px; }
.pair { display:flex; align-items:flex-end; justify-content:space-between; gap:6px; }
.side { display:flex; flex-direction:column; align-items:center; gap:3px; flex:1 1 0; }
.lab { font-size:9.5px; color:#8a7a60; letter-spacing:.5px; }
.draw { width:74px; height:74px; color:#7a6748; }
.orac { width:74px; height:74px; color:#2a2118; }
.arrow { font-size:16px; color:#a8321f; padding-bottom:26px; }
.nm { text-align:center; font-size:15px; font-weight:700; letter-spacing:1px;
      margin-top:5px; }
.fb { font-size:9.5px; color:#a8321f; font-weight:400; margin-left:4px; }
.missing { width:74px; height:74px; display:flex; align-items:center;
           justify-content:center; font-size:11px; color:#a8321f; }
</style></head><body>
<h1>试样：手绘实物 → 真实甲骨字形</h1>
<p class="lead">左边是我手写的 SVG 实物线描，右边是从 glyph-parts.json 取出的<b>真实甲骨字形</b>——
就是你地图上现在用的那一套。请重点看：<b>两边像不像</b>。实物图是按字形反推画的，
不是按现代实物自由发挥，所以「鼎」是三足两耳、「目」是横着的眼睛。</p>
<div class="grid">
%s
</div>
</body></html>""" % "".join(cells)

page = os.path.join(tempfile.gettempdir(), "zq_sample.html")
io.open(page, "w", encoding="utf-8").write(HTML)

tmp = os.path.join(tempfile.gettempdir(), "zq_sample_prof")
subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", tmp],
               capture_output=True)
shot = os.path.join(OUT, "sample_draw_vs_oracle.png")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + tmp, "--window-size=1140,1100",
                    "--screenshot=" + shot,
                    "--virtual-time-budget=6000", "file:///" + page.replace("\\", "/")],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=180)
print("试样页:", page)
print("截图:", shot, os.path.getsize(shot) if os.path.exists(shot) else 0, "B")
print("绘制了 %d 个试样，全部用真实字形对照" % len(CARDS))
missing = [c for c in CARDS if c not in parts]
print("缺字形:", "、".join(missing) if missing else "无")
