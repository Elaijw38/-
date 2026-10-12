/* ============================================================
   字趣 · 启动
   职责：注入品牌字形、套用主题、做存储迁移、启动路由。
   放在所有脚本之后加载，因此此刻 App 的各模块都已就绪。
   ============================================================ */
(function (App) {
  'use strict';

  /* ---------- 品牌信息 ---------- */
  App.BRAND = '甲骨构字记';
  App.BRAND_SUB = '用甲骨文构件拼出汉字';
  App.BRAND_SEAL = '试玩版';
  App.BRAND_VERSION = '0.2';

  /* ============================================================
     品牌字形：「甲骨」二字用数据集的真实甲骨文字形。
     来源 hanzi-glyphs-svg（CC BY 4.0）glyph_id 1023=甲、0315=骨；
     本项目做了缩放、配色与编排。运行期合成，可随主题变色。
     ============================================================ */
  var GLYPH_IDS = ['1023', '0315'];      /* 甲、骨 */
  var OB_INLINE = {
    /* 两个构件的矢量路径（viewBox 内为原始坐标，此处按高度统一缩放） */
    '1023': { vb: [3.58, 3.58, 18.06, 22.84],
      d: 'M 3.581 4.026 L 4.581 20.026 A 0.42 0.42 0 0 0 5.419 19.974 L 4.419 3.974 ' +
         'A 0.42 0.42 0 0 0 3.581 4.026 Z M 4 4.42 L 18 4.42 A 0.42 0.42 0 0 0 18 3.58 ' +
         'L 4 3.58 A 0.42 0.42 0 0 0 4 4.42 Z M 17.48 4 L 17.48 19 A 0.42 0.42 0 0 0 18.32 19 ' +
         'L 18.32 4 A 0.42 0.42 0 0 0 17.48 4 Z M 3.58 19.58 L 18.58 19.58 A 0.42 0.42 0 0 0 18.58 18.74 ' +
         'L 3.58 18.74 A 0.42 0.42 0 0 0 3.58 19.58 Z M 11 7 L 11 20 A 0.42 0.42 0 0 0 11.84 20 ' +
         'L 11.84 7 A 0.42 0.42 0 0 0 11 7 Z' },
    '0315': { vb: [4.40, 5.15, 20.6, 27.9],
      d: 'M 6 9 L 6 12 A 0.615 0.615 0 0 0 7.23 12 L 7.23 9 A 0.615 0.615 0 0 0 6 9 Z ' +
         'M 4.4 12.6 L 16 12.6 A 0.615 0.615 0 0 0 16 11.37 L 4.4 11.37 A 0.615 0.615 0 0 0 4.4 12.6 Z ' +
         'M 16.6 9 L 16.6 13 A 0.615 0.615 0 0 0 17.83 13 L 17.83 9 A 0.615 0.615 0 0 0 16.6 9 Z ' +
         'M 7.391 19.087 L 8.391 26.087 A 0.615 0.615 0 0 0 9.609 25.913 L 8.609 18.913 ' +
         'A 0.615 0.615 0 0 0 7.391 19.087 Z' }
  };

  function buildBrandGlyphURI(color) {
    var H = 64, PAD = 2, GAP = 12;
    var parts = [], x = 0;
    GLYPH_IDS.forEach(function (id) {
      var g = OB_INLINE[id];
      if (!g) return;
      var k = H / g.vb[3];
      var w = g.vb[2] * k;
      parts.push({ id: id, x: x, k: k, vb: g.vb, d: g.d, w: w });
      x += w + GAP;
    });
    if (!parts.length) return '';
    var totalW = x - GAP + PAD * 2;
    var body = parts.map(function (p) {
      var tx = p.x - p.vb[0] * p.k + PAD;
      var ty = -p.vb[1] * p.k + PAD;
      return '<g transform="translate(' + tx.toFixed(2) + ',' + ty.toFixed(2) + ') scale(' +
        p.k.toFixed(5) + ')"><path d="' + p.d + '" fill="' + color + '"/></g>';
    }).join('');
    var W = totalW, HH = H + PAD * 2;
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W.toFixed(1) +
      '" height="' + HH.toFixed(1) + '" viewBox="0 0 ' + W.toFixed(1) + ' ' + HH.toFixed(1) +
      '" role="img" aria-label="甲骨">' + body + '</svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  /* 品牌字形颜色：主题固定为骨白（浅底），取墨色 */
  function glyphColorFor() {
    return '#221d15';
  }

  /* ============================================================
     外观：固定为「骨白」浅色主题，站点不提供任何外观设置。
     html 上的 data-theme="bone" 只是让 css 里那套骨白变量生效的
     内部实现细节（css 以 [data-theme="bone"] 组织），用户看不到也改不了；
     不读取任何存储值，因此早期访客残留的 theme 设置不会影响显示。
     ============================================================ */
  function applyAppearance() {
    document.documentElement.setAttribute('data-theme', 'bone');
    App.brandGlyphURI = buildBrandGlyphURI(glyphColorFor());
    /* 已渲染的站点头需要重画（字形颜色变了） */
    if (App.shell && App.shell.renderHeader) App.shell.renderHeader();
  }

  /* ============================================================
     页面底纹：真实甲骨文字形，竖排成列
     ------------------------------------------------------------
     甲骨卜辞是**竖排成列**写的（自上而下、自右向左），所以底纹不撒点，
     而是排成竖列、立上列线，整页才像一片摊开的骨版。
     字形全部取自本项目的数据集（hanzi-glyphs-svg, CC BY 4.0），
     按笔画数挑简单的，顺序写死——每次打开底纹都一样，不是随机。
     另点缀几道「兆」：灼烧后裂开的纹，甲骨上最典型的痕迹。
     那是抽象的叉线，**不是字**，所以不涉及"编造字形"。
     ============================================================ */
  var PAT_TILE = 860;          /* 与 theme.css 里 --ob-pattern 的 background-size 对齐 */

  /* 底纹用字：笔画少、辨识度高。密了会糊成一片，所以只取 24 个。 */
  var PAT_CHARS = ['日', '月', '山', '水', '木', '火', '土', '田',
                   '人', '止', '生', '卜', '又', '力', '刀', '井',
                   '宀', '戈', '弓', '羊', '犬', '鱼', '雨', '石'];

  /* 确定性伪随机：同一个 i 永远得到同一个值，底纹因此稳定 */
  function patRand(i) {
    var x = Math.sin(i * 12.9898) * 43758.5453;
    return x - Math.floor(x);
  }

  function buildPatternURI() {
    var parts = (App.glyphs && App.glyphs.parts) || {};
    var avail = PAT_CHARS.filter(function (c) { return !!parts[c]; });
    if (!avail.length) { return ''; }

    var cols = 5, rows = 5;
    var colW = PAT_TILE / cols;
    var body = '';
    var n = 0, c, r, m;

    /* 列线：先立竖列，全局才有"版"的结构感 */
    for (c = 0; c < cols; c++) {
      var lx = (colW * (c + 0.5)).toFixed(1);
      body += '<path d="M' + lx + ' 36 L' + lx + ' ' + (PAT_TILE - 36) +
        '" stroke="#6b5f45" stroke-opacity=".15" stroke-width="1" fill="none"/>';
    }

    /* 字形：竖列自上而下 */
    for (c = 0; c < cols; c++) {
      for (r = 0; r < rows; r++) {
        n++;
        var ch = avail[(c * rows + r) % avail.length];
        var g = parts[ch];
        if (!g || !g.pieces || !g.pieces.length) { continue; }
        var size = 52 + Math.round(patRand(n) * 22);        /* 52~74，大小不齐才自然 */
        var k = size / 100;
        /* 字形自己的内层缩放：线宽要按它反算，各字在画布上才一样粗 */
        var km = /scale\(([\d.]+)\)/.exec(g.transform || '');
        var kg = km ? parseFloat(km[1]) : 1;
        /* 目标：画布 2.2 单位的线宽 → 内层 space 里就是 2.2 / kg */
        var sw = (kg > 0 ? (2.2 / kg) : 2.2).toFixed(4);
        var cx = colW * (c + 0.5) - size / 2 + (patRand(n + 100) - 0.5) * 16;
        var cy = (PAT_TILE / rows) * (r + 0.5) - size / 2 + (patRand(n + 200) - 0.5) * 18;
        var ds = g.pieces.map(function (p) { return p.d; }).join(' ');
        /* 加深到真的看得见：原先是 .10~.19，压在纸面上几乎等于没有，
           于是整页就是"一片空白"（用户的评价）。刻辞本来就该读得出来。 */
        body += '<g transform="translate(' + cx.toFixed(1) + ',' + cy.toFixed(1) +
          ') scale(' + k.toFixed(4) + ')" opacity="' +
          (0.20 + patRand(n + 300) * 0.14).toFixed(3) + '">' +
          '<g transform="' + g.transform + '">' +
          '<path d="' + ds + '" fill="none" stroke="#5d5340" stroke-width="' + sw +
          '" stroke-linecap="round" stroke-linejoin="round"/></g></g>';
      }
    }

    /* 兆：灼烧裂纹。甲骨上最常见的痕迹，抽象叉线，不是字。 */
    for (m = 0; m < 7; m++) {
      var mx = (patRand(m + 500) * PAT_TILE).toFixed(0);
      var my = (patRand(m + 600) * PAT_TILE).toFixed(0);
      var len = 46 + patRand(m + 700) * 74;
      body += '<path d="M' + mx + ' ' + my +
        ' L' + (+mx + len * 0.18).toFixed(0) + ' ' + (+my + len).toFixed(0) +
        ' M' + mx + ' ' + my +
        ' L' + (+mx - len * 0.42).toFixed(0) + ' ' + (+my + len * 0.78).toFixed(0) +
        '" fill="none" stroke="#6b5f45" stroke-opacity=".19" stroke-width="1.1"/>';
    }

    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + PAT_TILE +
      '" height="' + PAT_TILE + '" viewBox="0 0 ' + PAT_TILE + ' ' + PAT_TILE + '">' +
      body + '</svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  function injectPattern() {
    /* 底纹由真字形实时合成（见 buildPatternURI）。
       骨纹/斑驳那一层已改由 assets/bone.png 承担（见 dev/_gen_bone.py），
       所以这里不再另发一张 SVG 网格——两层纹理叠在一起只会互相糊掉。 */
    var ob = App.OB_PATTERN || buildPatternURI();
    document.documentElement.style.setProperty('--ob-pattern',
      ob ? ('url("' + ob + '")') : 'none');
  }

  /* ---------- 启动 ---------- */
  function boot() {
    injectPattern();
    applyAppearance();

    /* 清掉可能残留的临时类（例如上一次异常退出时留下的） */
    if (document.body.classList) document.body.classList.remove('challenging');

    /* 首次访问给一句引导 */
    if (!App.store.get('seen', false)) {
      App.store.set('seen', true);
      setTimeout(function () {
        App.toast('欢迎来到字趣。先选一个玩法开始吧。', 4200);
      }, 700);
    }

    App.router.start();

    /* 暴露给调试与自动化测试 */
    window.__ZQ__ = {
      version: App.BRAND_VERSION,
      modes: App.modes,
      packs: App.packs,
      router: App.router
    };
  }

  /* 本脚本是最后一个同步脚本，放在 </body> 之前：
     此刻 DOM 已解析完毕，直接启动即可，不必等 DOMContentLoaded
     （等它反而会让外部驱动脚本先于平台就绪运行）。 */
  boot();

})(window.App = window.App || {});
