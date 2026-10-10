/* ============================================================
   字趣 · 关卡与字形数据装载
   职责：把 levels.json 与 glyph-parts.json 暴露为 App.levels / App.glyphs。

   为什么不用 fetch？
     平台是「传统 script + 全局 App」架构，为的是能在 file:// 下双击直接打开。
     fetch 读本地 JSON 会被 CORS 拦（file:// 下 origin 为 null），
     因此这里用同目录的 _data.js 包裹 JSON（由 dev/_build_leveldata.py 生成），
     保持「双击即开、无需起服务器」这一既有决定。
   ============================================================ */
(function (App) {
  'use strict';

  App.levels = App.levels || null;
  App.glyphs = App.glyphs || null;

  /* 取某字形的内联 SVG（描边占位 {C} 替换为实际颜色） */
  App.glyphSvg = function (name, color) {
    var g = App.glyphs && App.glyphs.parts ? App.glyphs.parts[name] : null;
    if (!g) return '';
    return g.svg.replace(/\{C\}/g, color || 'currentColor');
  };

  /* 该字是否有甲骨字形 */
  App.hasGlyph = function (name) {
    return !!(App.glyphs && App.glyphs.parts && App.glyphs.parts[name]);
  };

})(window.App = window.App || {});
