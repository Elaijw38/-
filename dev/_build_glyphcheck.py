# -*- coding: utf-8 -*-
"""生成 _glyphcheck.html —— 全部收录字形对照 + 越界检查。"""
import json, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _glyphdata import build_svg

ROOT = r"C:\DSH\字趣"
d = json.loads(io.open(os.path.join(ROOT, "js", "core", "glyph-parts.json"), encoding="utf-8").read())
canvas = d["canvas"]
parts = d["parts"]

cells = []
for name in sorted(parts.keys()):
    p = parts[name]
    svg = build_svg(p, "currentColor")
    star = ' <em>*</em>' if p.get("isFallback") else ''
    cells.append('<div class="cell"><svg viewBox="0 0 @C@ @C@">@S@</svg>'
                 '<span class="nm">@N@@ST@</span><span class="id">@ID@</span></div>'
                 .replace("@C@", str(canvas)).replace("@S@", svg)
                 .replace("@N@", name).replace("@ST@", star)
                 .replace("@ID@", str(p["glyphId"])))

tpl = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>甲骨字形对照</title><style>
body{background:#f0e6d2;color:#221d15;font-family:serif;padding:16px;margin:0}
h3{font-size:14px;margin:10px 0 8px;color:#6b5f4b;border-left:3px solid #a8321f;padding-left:8px}
h3 small{font-weight:400;color:#8a7a60;font-size:11px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(76px,1fr));gap:7px;max-width:1080px}
.cell{background:#faf4e6;border:1px solid #b59a6e;border-radius:6px;padding:5px 3px 3px;text-align:center}
.cell svg{width:48px;height:48px;display:block;margin:0 auto;color:#221d15}
.nm{display:block;font-size:13px;margin-top:2px}
.id{display:block;font-size:8px;color:#8a7a60}
em{color:#a8321f;font-style:normal}
</style></head><body>
<h3>全部收录字形 <small>（@COUNT@ 个；<em>*</em> = 借用代用）</small></h3>
<div class="grid">@CELLS@</div>
<script>
setTimeout(function () {
  var CANVAS = @CANVAS@, bad = [], small = [], none = [];
  document.querySelectorAll('.cell').forEach(function (c) {
    var svg = c.querySelector('svg'), g = svg.querySelector('g'), p = svg.querySelector('path');
    var nm = c.querySelector('.nm').textContent.trim();
    if (!g || !p) { none.push(nm); return; }
    var bb = p.getBBox(), m = g.transform.baseVal.consolidate().matrix, xs = [], ys = [];
    [[bb.x, bb.y], [bb.x + bb.width, bb.y], [bb.x, bb.y + bb.height], [bb.x + bb.width, bb.y + bb.height]]
      .forEach(function (q) {
        var v = svg.createSVGPoint(); v.x = q[0]; v.y = q[1];
        var t = v.matrixTransform(m); xs.push(t.x); ys.push(t.y);
      });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    if (x0 < -1 || y0 < -1 || x1 > CANVAS + 1 || y1 > CANVAS + 1) {
      bad.push(nm + '[' + x0.toFixed(0) + ',' + y0.toFixed(0) + '-' + x1.toFixed(0) + ',' + y1.toFixed(0) + ']');
    }
    if ((x1 - x0) < CANVAS * 0.35 && (y1 - y0) < CANVAS * 0.35) small.push(nm);
  });
  document.documentElement.setAttribute('data-result',
    'cells=' + document.querySelectorAll('.cell').length +
    ' | 越界=' + (bad.length ? bad.join(',') : '无') +
    ' | 过小=' + (small.length ? small.join(',') : '无') +
    ' | 无路径=' + (none.length ? none.join(',') : '无'));
}, 800);
</script></body></html>"""

html = (tpl.replace("@CELLS@", "".join(cells))
           .replace("@CANVAS@", str(canvas))
           .replace("@COUNT@", str(len(parts))))
io.open(os.path.join(ROOT, "_glyphcheck.html"), "w", encoding="utf-8").write(html)
print("written:", os.path.getsize(os.path.join(ROOT, "_glyphcheck.html")), "bytes,", len(parts), "glyphs")
