/* ============================================================
   字趣 · 玩法模块：殷商王邑（实物地图 · 点击即学）

   一句话：一张三千年前的王邑地图，上面散布着实物；
   点哪个实物，就学哪个甲骨文。

   为什么是「实物点」而不是「区块闯关」：
     起初按闯关做（区块 → 关卡 → 答题），方向错了。
     要的是"看图认字"——地图即教材，实物即词条，点开就学，
     所以没有关卡、没有解锁闸门、没有倒计时。
     每个实物都是独立词条，随时可点，学过的会记下来。

   数据全在 js/core/levels.json 的 map.zones[].objects：
     { char:字, x, y, meaning:象形说明 }
   改数据即可增删实物，本文件不含任何写死的字表。

   兼容：
     原答题型关卡（拆字/配对/卜辞）仍保留在 levels.json 的 map.quiz 下，
     地图底部留一个入口切过去，不丢已有功能。
   ============================================================ */
(function (App) {
  'use strict';

  var MAP = (App.levels && App.levels.map) || null;
  var STORE_KEY = 'wangyi';

  /* ---------- 学习记录 ----------
     { seen: { zoneId: [已看过的字, ...] } }
     复用平台统一的 ziqu. 前缀存储。 */
  function progress() {
    var p = App.store.get(STORE_KEY, null);
    if (!p || typeof p !== 'object') p = {};
    if (!p.seen || typeof p.seen !== 'object') p.seen = {};
    return p;
  }
  function saveProgress(p) { App.store.set(STORE_KEY, p); }
  function seenList(p, zoneId) { return p.seen[zoneId] || []; }
  function isSeen(p, zoneId, ch) { return seenList(p, zoneId).indexOf(ch) >= 0; }
  function markSeen(zoneId, ch) {
    var p = progress();
    if (!p.seen[zoneId]) p.seen[zoneId] = [];
    if (p.seen[zoneId].indexOf(ch) < 0) { p.seen[zoneId].push(ch); saveProgress(p); }
    return p;
  }
  function seenTotal(p) {
    var n = 0;
    (MAP.zones || []).forEach(function (z) { n += seenList(p, z.id).length; });
    return n;
  }
  function objectTotal() {
    var n = 0;
    (MAP.zones || []).forEach(function (z) { n += (z.objects || []).length; });
    return n;
  }
  function findObject(ch) {
    var hit = null;
    (MAP.zones || []).forEach(function (z) {
      (z.objects || []).forEach(function (o) { if (o.char === ch) hit = { zone: z, obj: o }; });
    });
    return hit;
  }

  /* 每个实物画成什么：地图上的实物点用「甲骨字形」本身表示——
     甲骨文本来就是象形的，山像山、木像木，用它当实物图标最贴切，
     也省掉另造一套插画素材。下方再标今字，便于对上。 */
  var CANVAS = 100;
  var SVGNS = 'http://www.w3.org/2000/svg';

  function glyphInto(parent, ch, size, cls) {
    var g = App.glyphSvg(ch, 'currentColor');
    if (!g) return false;
    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + CANVAS + ' ' + CANVAS);
    svg.setAttribute('class', cls || '');
    svg.setAttribute('aria-hidden', 'true');
    svg.style.width = size + 'px';
    svg.style.height = size + 'px';
    svg.innerHTML = g;
    parent.appendChild(svg);
    return true;
  }

  /* ============================================================
     挂载
     ============================================================ */
  function mount(host, ctx) {
    /* 每次挂载都回到地图，并清掉上一次的选择（S 是模块级状态） */
    S.view = 'map';
    S.sel = null;

    var root = App.el('div', 'scene wangyi');
    host.appendChild(root);

    if (!MAP || !MAP.zones || !MAP.zones.length) {
      root.appendChild(App.el('p', 'lead', '地图数据缺失（js/core/levels.json）。'));
      return;
    }

    function render() {
      App.clearNode(root);
      if (S.view === 'detail' && S.sel) { renderDetail(root); return; }
      if (S.view === 'quiz') { renderQuizEntry(root); return; }
      renderMap(root);
    }

    /* ---------- 地图 ---------- */
    function renderMap(el) {
      var p = progress();
      var total = objectTotal();
      var seen = seenTotal(p);

      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', MAP.name));
      head.appendChild(App.el('span', 'wy-sub', MAP.subtitle || ''));
      el.appendChild(head);
      el.appendChild(App.el('p', 'lead', MAP.intro || ''));

      /* 学习进度：认过的实物数 */
      var bar = App.el('div', 'wy-learnbar');
      bar.appendChild(App.el('span', 'wy-learnnum', seen + ' / ' + total));
      bar.appendChild(App.el('span', 'wy-learnword', '个实物已认'));
      var meter = App.el('span', 'wy-meter');
      var fill = App.el('i', 'wy-meter-fill');
      fill.style.width = (total ? (seen / total * 100) : 0) + '%';
      meter.appendChild(fill);
      bar.appendChild(meter);
      el.appendChild(bar);

      var svg = document.createElementNS(SVGNS, 'svg');
      svg.setAttribute('class', 'wy-omap');
      svg.setAttribute('viewBox', MAP.viewBox || '0 0 1240 880');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', MAP.name + '：点击实物认甲骨文');
      svg.appendChild(buildBackdrop());

      /* 逐区摆放实物 */
      (MAP.zones || []).forEach(function (z) {
        var objs = z.objects || [];
        if (!objs.length) return;

        /* 区块标题位置直接取自数据（titleX/titleY）。
           早先按「最上实物再上移」推导，结果被高处的日月顶到地图中部，
           压住了下方的实物——所以改成数据里显式给坐标，并有自检把关。 */
        var bb = bbox(objs);
        var tx = (typeof z.titleX === 'number') ? z.titleX : bb.x0;
        var ty = (typeof z.titleY === 'number') ? z.titleY : Math.max(40, bb.y0 - 90);

        var zt = document.createElementNS(SVGNS, 'text');
        zt.setAttribute('x', tx);
        zt.setAttribute('y', ty);
        zt.setAttribute('class', 'wy-zone-title');
        zt.textContent = z.name || '';
        svg.appendChild(zt);
        if (z.note) {
          var zn = document.createElementNS(SVGNS, 'text');
          zn.setAttribute('x', tx);
          zn.setAttribute('y', ty + 24);
          zn.setAttribute('class', 'wy-zone-note');
          zn.textContent = z.note;
          svg.appendChild(zn);
        }

        objs.forEach(function (o) {
          var seenThis = isSeen(p, z.id, o.char);
          var g = document.createElementNS(SVGNS, 'g');
          g.setAttribute('class', 'wy-obj' + (seenThis ? ' seen' : '') +
            (S.sel === o.char ? ' sel' : ''));
          g.setAttribute('transform', 'translate(' + o.x + ',' + o.y + ')');
          g.setAttribute('tabindex', '0');
          g.setAttribute('role', 'button');
          g.setAttribute('aria-label', o.char + '，' + (o.meaning || ''));

          /* 点击热区（比字形大一圈，方便点中） */
          var hit = document.createElementNS(SVGNS, 'circle');
          hit.setAttribute('r', 42);
          hit.setAttribute('class', 'wy-obj-hit');
          g.appendChild(hit);

          var box = document.createElementNS(SVGNS, 'g');
          box.setAttribute('transform', 'translate(-27,-34)');
          var rect = document.createElementNS(SVGNS, 'rect');
          rect.setAttribute('width', 54);
          rect.setAttribute('height', 54);
          rect.setAttribute('rx', 8);
          rect.setAttribute('class', 'wy-obj-box');
          box.appendChild(rect);

          var form = document.createElementNS(SVGNS, 'g');
          form.setAttribute('class', 'wy-obj-form');
          form.setAttribute('transform', 'translate(3,3) scale(0.48)');
          form.innerHTML = App.glyphSvg(o.char, 'currentColor');
          box.appendChild(form);
          g.appendChild(box);

          var lab = document.createElementNS(SVGNS, 'text');
          lab.setAttribute('y', 40);
          lab.setAttribute('class', 'wy-obj-label');
          lab.setAttribute('text-anchor', 'middle');
          lab.textContent = o.char;
          g.appendChild(lab);

          if (seenThis) {
            var tick = document.createElementNS(SVGNS, 'circle');
            tick.setAttribute('cx', 22);
            tick.setAttribute('cy', -28);
            tick.setAttribute('r', 6);
            tick.setAttribute('class', 'wy-obj-tick');
            g.appendChild(tick);
          }

          function pick() { select(z, o); }
          g.onclick = pick;
          g.onkeydown = function (ev) {
            if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(); }
          };
          svg.appendChild(g);
        });
      });

      el.appendChild(svg);

      var legend = App.el('div', 'wy-legend');
      var l1 = App.el('span', 'wy-lg');
      l1.appendChild(App.el('i', 'wy-lg-dot'));
      l1.appendChild(document.createTextNode('点实物看甲骨文'));
      legend.appendChild(l1);
      var l2 = App.el('span', 'wy-lg');
      l2.appendChild(App.el('i', 'wy-lg-dot seen'));
      l2.appendChild(document.createTextNode('已认过的会点上印记'));
      legend.appendChild(l2);
      el.appendChild(legend);

      var side = App.el('div', 'wy-side');
      if (MAP.quiz && MAP.quiz.zones && MAP.quiz.zones.length) {
        var q = App.el('button', 'btn sm', '去答题练习（拆字 / 配对 / 卜辞）');
        q.onclick = function () { S.view = 'quiz'; render(); };
        side.appendChild(q);
      }
      var modes = App.el('button', 'btn sm', '原有的单字选构练习');
      modes.onclick = function () { ctx.nav.modes(); };
      side.appendChild(modes);
      var reset = App.el('button', 'btn sm', '重置学习记录');
      reset.onclick = function () {
        if (!window.confirm('清空已认过的实物记录？')) return;
        App.store.del(STORE_KEY);
        render();
      };
      side.appendChild(reset);
      el.appendChild(side);
    }

    function select(zone, obj) {
      markSeen(zone.id, obj.char);
      S.sel = obj.char;
      S.view = 'detail';
      S.selZone = zone;
      render();
    }

    /* ---------- 实物详情（学习卡） ---------- */
    function renderDetail(el) {
      var o = S.sel;
      var zone = S.selZone;
      var hit = findObject(o);
      if (hit) { zone = hit.zone; o = hit.obj; }
      var p = progress();

      var back = App.el('button', 'btn sm', '← 回到地图');
      back.onclick = function () { S.view = 'map'; S.sel = null; render(); };
      el.appendChild(back);

      var card = App.el('div', 'wy-card');

      var big = App.el('div', 'wy-card-form');
      if (!glyphInto(big, o.char, 190, 'wy-big')) {
        big.appendChild(App.el('div', 'wy-glyph-none', '（缺字形）'));
      }
      card.appendChild(big);

      var info = App.el('div', 'wy-card-info');
      var row = App.el('div', 'wy-card-row');
      row.appendChild(App.el('span', 'wy-card-char', o.char));
      row.appendChild(App.el('span', 'wy-card-zone', (zone && zone.name) || ''));
      info.appendChild(row);
      info.appendChild(App.el('div', 'wy-card-mean', o.meaning || ''));

      var gl = (App.glyphs && App.glyphs.parts) ? App.glyphs.parts[o.char] : null;
      if (gl && gl.sourceChar && gl.sourceChar !== o.char) {
        info.appendChild(App.el('div', 'wy-card-note',
          '数据集中的字形对应「' + gl.sourceChar + '」（glyphId ' + gl.glyphId + '）'));
      }
      if (gl && gl.isFallback) {
        info.appendChild(App.el('div', 'wy-card-note',
          '※ 数据集未收录此字，借用其形代用。'));
      }
      card.appendChild(info);
      el.appendChild(card);

      /* 认识一下其它实物：给几个同类字，顺着看下去 */
      if (zone && zone.objects && zone.objects.length > 1) {
        var more = App.el('div', 'wy-more');
        more.appendChild(App.el('div', 'wy-more-title', '同区其它实物'));
        var strip = App.el('div', 'wy-more-strip');
        zone.objects.forEach(function (sib) {
          if (sib.char === o.char) return;
          var b = App.el('button', 'wy-mini' + (isSeen(p, zone.id, sib.char) ? ' seen' : ''));
          if (!glyphInto(b, sib.char, 40, 'wy-mini-glyph')) {
            b.appendChild(App.el('span', 'wy-glyph-none', sib.char));
          }
          b.appendChild(App.el('span', 'wy-mini-name', sib.char));
          b.title = sib.meaning || sib.char;
          b.onclick = function () {
            markSeen(zone.id, sib.char);
            S.sel = sib.char;
            render();
          };
          strip.appendChild(b);
        });
        more.appendChild(strip);
        el.appendChild(more);
      }

      var bar = App.el('div', 'wy-side');
      var prev = ElPrevNext();
      bar.appendChild(prev[0]);
      bar.appendChild(prev[1]);
      el.appendChild(bar);
    }

    /* 上一个 / 下一个：按地图顺序，方便顺着一个个认下去 */
    function ElPrevNext() {
      var flat = [];
      (MAP.zones || []).forEach(function (z) {
        (z.objects || []).forEach(function (o) { flat.push({ z: z, o: o }); });
      });
      var i = -1;
      flat.forEach(function (it, k) { if (it.o.char === S.sel) i = k; });
      function go(k) {
        var it = flat[(k + flat.length) % flat.length];
        markSeen(it.z.id, it.o.char);
        S.sel = it.o.char;
        S.selZone = it.z;
        render();
      }
      var a = App.el('button', 'btn sm', '← 上一个');
      a.disabled = flat.length < 2;
      a.onclick = function () { go(i - 1); };
      var b = App.el('button', 'btn sm', '下一个 →');
      b.disabled = flat.length < 2;
      b.onclick = function () { go(i + 1); };
      return [a, b];
    }

    /* ---------- 答题练习入口（保留原有玩法） ---------- */
    function renderQuizEntry(el) {
      var back = App.el('button', 'btn sm', '← 回到地图');
      back.onclick = function () { S.view = 'map'; render(); };
      el.appendChild(back);

      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', '答题练习'));
      el.appendChild(head);
      el.appendChild(App.el('p', 'lead',
        '这里是原来的答题型玩法。想看图上认字，回地图点实物即可。'));

      var wrap = App.el('div', 'wy-zlist');
      (MAP.quiz.zones || []).forEach(function (z, idx) {
        var b = App.el('button', 'wy-zbtn');
        b.appendChild(App.el('span', 'wy-zb-name', z.name));
        b.appendChild(App.el('span', 'wy-zb-meta',
          (z.mechanic || '') + ' · ' + (z.levels || []).length + ' 关'));
        b.onclick = function () {
          App.toast('答题玩法暂未在地图内启用，可先用「原有的单字选构练习」。');
        };
        wrap.appendChild(b);
      });
      el.appendChild(wrap);
    }

    /* ---------- 地图背景：一张淡墨实景 ----------
       只为让实物"落在地上"，不抢主角；线条都很淡。 */
    function buildBackdrop() {
      var g = document.createElementNS(SVGNS, 'g');
      g.setAttribute('class', 'wy-backdrop');
      g.innerHTML = [
        /* 远山 */
        '<path class="wy-bd-hill" d="M0,300 L120,210 L210,275 L330,175 L470,300 Z"/>',
        '<path class="wy-bd-hill" d="M700,300 L820,205 L930,265 L1060,168 L1240,300 Z"/>',
        /* 河流：自左上斜贯至右下 */
        '<path class="wy-bd-river" d="M0,430 C160,400 250,500 400,505 '
        + 'C560,510 640,470 780,505 C930,545 1080,505 1240,545"/>',
        /* 田亩纹 */
        '<g class="wy-bd-field">'
        + '<path d="M80,520 h360 M80,548 h360 M80,576 h360"/>'
        + '<path d="M120,505 v95 M200,505 v95 M280,505 v95 M360,505 v95"/>'
        + '</g>',
        /* 树丛剪影 */
        '<g class="wy-bd-tree">'
        + '<path d="M470,830 v-70 M445,780 l25,-30 l25,30 M450,800 l20,-24 l20,24"/>'
        + '<path d="M960,860 v-70 M935,810 l25,-30 l25,30 M940,830 l20,-24 l20,24"/>'
        + '</g>',
        /* 地层线 */
        '<path class="wy-bd-ground" d="M0,700 H1240"/>'
      ].join('');
      return g;
    }

    function bbox(objs) {
      var x0 = Infinity, y0 = Infinity;
      objs.forEach(function (o) {
        if (o.x < x0) x0 = o.x;
        if (o.y < y0) y0 = o.y;
      });
      return { x0: Math.max(20, x0 - 34), y0: y0 };
    }

    render();
  }

  var S = { view: 'map', sel: null, selZone: null };

  function unmount() { S.view = 'map'; S.sel = null; S.selZone = null; }

  App.modes.register({
    id: 'wangyi-map',
    name: '殷商王邑',
    tagline: '点地图上的实物，认甲骨文',
    desc: '一张三千年前的王邑地图。山川草木、禽兽虫鱼、人居器物都在图上，'
        + '点哪一样，就看古人把它画成什么字。看过的会点上一枚印记。',
    icon: '邑',
    accent: 'var(--bronze)',
    tags: ['看图认字', '61 个实物', '随点随学'],
    minPlayers: 1, maxPlayers: 1,
    status: 'ready',
    data: { packs: [], assets: [] },
    mount: mount,
    unmount: unmount
  });

})(window.App = window.App || {});
