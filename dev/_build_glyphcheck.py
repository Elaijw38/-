# -*- coding: utf-8 -*-
"""生成 _glyphcheck.html —— 37 个构件甲骨字形的可视对照 + 越界检查。"""
import json, io, os

ROOT = r"C:\DSH\字趣"
d = json.loads(io.open(os.path.join(ROOT, "js", "core", "glyph-parts.json"), encoding="utf-8").read())
canvas = d["canvas"]

cells = []
for name, p in d["parts"].items():
    svg = p["svg"].replace("{C}", "currentColor")
    star = ' <em>*</em>' if p.get("isFallback") else ''
    cells.append(
        '<div class="cell"><svg viewBox="0 0 @C@ @C@">@S@</svg>'
        '<span class="nm">@N@@ST@</span><span class="id">@ID@</span></div>'
        .replace("@C@", str(canvas)).replace("@S@", svg)
        .replace("@N@", name).replace("@ST@", star).replace("@ID@", str(p["glyphId"])))

# 注意：下面这段脚本里也有 %s 之类的字样会给 JS 用，
# 因此整份模板一律用 @TOKEN@ 显式替换，绝不能用 Python 的 % 格式化
# （曾因此把 cells 塞进了 JS 占位符，页面只剩一个 "100.0"）。
tpl = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>甲骨构件对照</title><style>
body{background:#f0e6d2;color:#221d15;font-family:serif;padding:18px;margin:0}
h3{font-size:15px;margin:0 0 10px;color:#6b5f4b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:8px;max-width:1000px}
.cell{background:#faf4e6;border:1px solid #b59a6e;border-radius:6px;padding:6px 4px 4px;text-align:center}
.cell svg{width:56px;height:56px;display:block;margin:0 auto;color:#221d15}
.nm{display:block;font-size:14px;margin-top:3px}
.id{display:block;font-size:9px;color:#8a7a60}
em{color:#a8321f;font-style:normal}
</style></head><body>
<h3>37 个构件的甲骨字形（<em>*</em> = 借用代用）</h3>
<div class="grid">@CELLS@</div>
<script>
setTimeout(function () {
  var CANVAS = @CANVAS@;
  var bad = [], over = [], empty = [];
  document.querySelectorAll('.cell').forEach(function (c) {
    var svg = c.querySelector('svg');
    var g = svg.querySelector('g'), p = svg.querySelector('path');
    var nm = c.querySelector('.nm').textContent.trim();
    if (!g || !p) { empty.push(nm); return; }
    var bb = p.getBBox();
    var m = g.transform.baseVal.consolidate().matrix;
    var xs = [], ys = [];
    [[bb.x, bb.y], [bb.x + bb.width, bb.y], [bb.x, bb.y + bb.height], [bb.x + bb.width, bb.y + bb.height]]
      .forEach(function (q) {
        var v = svg.createSVGPoint(); v.x = q[0]; v.y = q[1];
        var t = v.matrixTransform(m);
        xs.push(t.x); ys.push(t.y);
      });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    if (x0 < -1 || y0 < -1 || x1 > CANVAS + 1 || y1 > CANVAS + 1) {
      bad.push(nm + ' [' + x0.toFixed(1) + ',' + y0.toFixed(1) + '-' + x1.toFixed(1) + ',' + y1.toFixed(1) + ']');
    }
    var w = x1 - x0, h = y1 - y0;
    if (w < CANVAS * 0.35 && h < CANVAS * 0.35) over.push(nm + '(' + w.toFixed(0) + 'x' + h.toFixed(0) + ')');
  });
  document.documentElement.setAttribute('data-result',
    'cells=' + document.querySelectorAll('.cell').length +
    ' | 越界=' + (bad.length ? bad.join(',') : '无') +
    ' | 过小=' + (over.length ? over.join(',') : '无') +
    ' | 无路径=' + (empty.length ? empty.join(',') : '无'));
}, 700);
</script></body></html>"""

html = (tpl.replace("@CELLS@", "".join(cells))
           .replace("@CANVAS@", str(canvas)))
io.open(os.path.join(ROOT, "_glyphcheck.html"), "w", encoding="utf-8").write(html)
print("written:", os.path.getsize(os.path.join(ROOT, "_glyphcheck.html")), "bytes,", len(cells), "cells")
