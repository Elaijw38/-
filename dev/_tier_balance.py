# -*- coding: utf-8 -*-
"""三档徽记的复杂度校准：一阶加料、三阶降噪。

用户反馈原话：「一阶太简单 三阶太复杂」。
原因：
  一阶原来只有三个字形排成一行、间距 2，视觉上只剩三根小棍 → 太素；
  三阶原来四个字叠压 + 旋转 ±9°，线条糊成一团 → 看不懂是什么。

改法：
  一阶：4 块字形按 2×2 拼在一起，**之间画接缝虚线**，既丰富又明确"这是拼起来的"；
  三阶：降到 2 个字，旋转 ±5°、透明度 1/.55，读作"同一个身体上纹路重了一层"，
        而不是一团乱线。
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "js", "modes", "boss-raid.js")
t = io.open(P, encoding="utf-8").read()

# ① 一阶：构件从 3 个加到 4 个
t = t.replace("glyphs: ['牛', '羊', '犬'], mode: 'gaps',",
              "glyphs: ['牛', '羊', '犬', '豕'], mode: 'gaps',")

# ② 三阶：从 4 个字降到 2 个字
t = t.replace("glyphs: ['虎', '鹿', '龜', '龍'], mode: 'tangled',",
              "glyphs: ['虎', '龜'], mode: 'tangled',")

# ③ 一阶摆位：2×2 + 接缝线
old_gaps = """       if (art.mode === 'gaps') {
         var n = list.length, gap = 2;
         var s = (96 - gap * (n - 1)) / n / 100;
         list.forEach(function (c, k) {
           var x = 2 + k * (s * 100 + gap);
           inner += '<g transform="translate(' + x.toFixed(2) + ',4) scale(' + s.toFixed(4) + ')">' +
             App.glyphSvg(c, 'currentColor') + '</g>';
         });"""
# 兼容缩进差异：不用精确锚点，改为整段替换（见下）
old_gaps_a = "if (art.mode === 'gaps') {"
assert t.count(old_gaps_a) == 1

start = t.index(old_gaps_a)
end = t.index("} else if (art.mode === 'tangled') {", start)
new_gaps = """if (art.mode === 'gaps') {
      /* 拼合：4 块字形按 2×2 拼在一起，块与块之间画**接缝虚线**，
         让"由构件拼成"一眼可读，同时不至于像原来那样只剩三根小棍。 */
      var CELL = [[2, 2], [52, 2], [2, 52], [52, 52]];
      list.forEach(function (c, k) {
        var q = CELL[k] || [2, 2];
        inner += '<g transform="translate(' + q[0] + ',' + q[1] + ') scale(.46)">' +
          App.glyphSvg(c, 'currentColor') + '</g>';
      });
      inner += '<g stroke="currentColor" stroke-width=".7" stroke-dasharray="2 2.6" opacity=".42">' +
        '<line x1="50" y1="4" x2="50" y2="96"/>' +
        '<line x1="4" y1="50" x2="96" y2="50"/></g>';
    """
t = t[:start] + new_gaps + t[end:]

# ④ 三阶：降低旋转与叠压
t = t.replace("var rots = [-9, 7, -4, 5], ops = [1, 0.62, 0.46, 0.34];",
              "var rots = [-5, 4], ops = [1, 0.55];")
t = t.replace("rotate(' + (rots[k] || 0) + ' 50 50) scale(.86)\" opacity=\"'",
              "rotate(' + (rots[k] || 0) + ' 50 50) scale(.90)\" opacity=\"'")
t = t.replace("var dx = (k % 2 ? 6 : -6), dy = (k * 4) - 6;",
              "var dx = (k % 2 ? 4 : -4), dy = (k * 3) - 3;")

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("  一阶 4 块 + 接缝虚线；三阶 2 字、旋转 ±5°")
