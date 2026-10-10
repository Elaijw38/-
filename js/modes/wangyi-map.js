/* ============================================================
   字趣 · 玩法模块：殷商王邑（实物地图 · 点击即学）

   一句话：一张三千年前的王邑图卷，点画上的实物，认那个甲骨文。

   设计要点：
     · 底图是整幅水墨图卷（assets/wangyi-map.jpg），**画上不画任何字形标记**，
       保持画面完整。
     · 在画里真实实物（山、河、鼎、弓箭手、牲口、屋舍…）的位置放【隐形热区】，
       点它就出学习卡。
     · 悬停时热区位置浮出该字的甲骨字形（鼠标用户能发现）；
       触屏用户可用「显示可点处」把 61 处热区显形。
     · 学过的实物在角上点一枚很小的绿点，作为进度痕迹，不遮挡画面。

   数据全在 js/core/levels.json 的 map.zones[].objects：
     { char:字, x, y（圆心）, r:热区半径, meaning:象形说明 }
   改数据即可增删实物，本文件不含任何写死的字表。
   ============================================================ */
(function (App) {
  'use strict';

  var MAP = (App.levels && App.levels.map) || null;
  var STORE_KEY = 'wangyi';
  var SVGNS = 'http://www.w3.org/2000/svg';
  var CANVAS = 100;              /* 字形画布 */

  /* ---------- 学习记录 ----------
     { seen: { zoneId: [已看过的字, ...] } } */
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
  function flatObjects() {
    var out = [];
    (MAP.zones || []).forEach(function (z) {
      (z.objects || []).forEach(function (o) { out.push({ zone: z, obj: o }); });
    });
    return out;
  }

  function svgEl(tag) { return document.createElementNS(SVGNS, tag); }

  /* ============================================================
     挂载
     ============================================================ */
  function mount(host, ctx) {
    S.view = 'map';
    S.sel = null;
    S.selZone = null;
    S.showHot = false;

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

    /* ---------- 地图（图卷 + 隐形热区） ---------- */
    function renderMap(el) {
      var p = progress();
      var total = objectTotal();
      var seen = seenTotal(p);

      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', MAP.name));
      head.appendChild(App.el('span', 'wy-sub', MAP.subtitle || ''));
      el.appendChild(head);

      var bar = App.el('div', 'wy-learnbar');
      bar.appendChild(App.el('span', 'wy-learnnum', seen + ' / ' + total));
      bar.appendChild(App.el('span', 'wy-learnword', '个实物已认'));
      var meter = App.el('span', 'wy-meter');
      var fill = App.el('i', 'wy-meter-fill');
      fill.style.width = (total ? (seen / total * 100) : 0) + '%';
      meter.appendChild(fill);
      bar.appendChild(meter);

      /* 「显示可点处」：默认关（保持画面干净），开了才把热区显形。
         触屏没有悬停，所以这个开关是必需的可发现性手段。 */
      var toggle = App.el('button', 'btn sm wy-hotbtn' + (S.showHot ? ' on' : ''),
        S.showHot ? '隐藏可点处' : '显示可点处（' + total + ' 处）');
      toggle.onclick = function () { S.showHot = !S.showHot; render(); };
      bar.appendChild(toggle);
      el.appendChild(bar);

      var wrap = App.el('div', 'wy-map' + (S.showHot ? ' show-hots' : ''));
      var svg = svgEl('svg');
      svg.setAttribute('class', 'wy-omap');
      svg.setAttribute('viewBox', MAP.viewBox || '0 0 1800 907');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', MAP.name + '：点击画上的实物认甲骨文');

      var vb = String(MAP.viewBox || '0 0 1800 907').split(/\s+/);

      /* 底图：整幅图卷 */
      if (MAP.bgImage) {
        var img = svgEl('image');
        img.setAttribute('x', 0);
        img.setAttribute('y', 0);
        img.setAttribute('width', vb[2] || 1800);
        img.setAttribute('height', vb[3] || 907);
        img.setAttribute('preserveAspectRatio', 'xMidYMid slice');
        img.setAttribute('href', MAP.bgImage);
        svg.appendChild(img);
      }

      /* 隐形热区 */
      flatObjects().forEach(function (it) {
        var z = it.zone;
        var o = it.obj;
        var r = o.r || 30;
        var seenThis = isSeen(p, z.id, o.char);

        var g = svgEl('g');
        g.setAttribute('class', 'wy-spot' + (seenThis ? ' seen' : '') +
          (S.sel === o.char ? ' sel' : ''));
        g.setAttribute('transform', 'translate(' + o.x + ',' + o.y + ')');
        g.setAttribute('tabindex', '0');
        g.setAttribute('role', 'button');
        g.setAttribute('aria-label', o.char + '，' + (o.meaning || ''));

        /* 命中区（透明） */
        var hit = svgEl('circle');
        hit.setAttribute('r', r);
        hit.setAttribute('class', 'wy-hot');
        g.appendChild(hit);

        /* 热区轮廓：平时不可见，开了「显示可点处」或悬停才显 */
        var ring = svgEl('circle');
        ring.setAttribute('r', r);
        ring.setAttribute('class', 'wy-ring');
        g.appendChild(ring);

        /* 悬停浮出的字形小牌 */
        var pop = svgEl('g');
        pop.setAttribute('class', 'wy-pop');
        var pbg = svgEl('circle');
        pbg.setAttribute('r', 28);
        pbg.setAttribute('class', 'wy-pop-bg');
        pop.appendChild(pbg);
        var form = svgEl('g');
        form.setAttribute('class', 'wy-pop-form');
        form.setAttribute('transform', 'translate(-20,-22) scale(0.4)');
        if (App.glyphSvg(o.char)) {
          form.innerHTML = App.glyphSvg(o.char, 'currentColor');
        }
        pop.appendChild(form);
        var lab = svgEl('text');
        lab.setAttribute('class', 'wy-pop-label');
        lab.setAttribute('text-anchor', 'middle');
        lab.setAttribute('y', 46);
        lab.textContent = o.char;
        pop.appendChild(lab);
        g.appendChild(pop);

        /* 已认：一枚很小的绿点，不挡画 */
        if (seenThis) {
          var dot = svgEl('circle');
          dot.setAttribute('cx', r - 5);
          dot.setAttribute('cy', -r + 5);
          dot.setAttribute('r', 4.5);
          dot.setAttribute('class', 'wy-seen-dot');
          g.appendChild(dot);
        }

        function pick() { select(z, o); }
        g.onclick = pick;
        g.onkeydown = function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(); }
        };
        svg.appendChild(g);
      });

      wrap.appendChild(svg);
      el.appendChild(wrap);

      var foot = App.el('div', 'wy-mapfoot');
      foot.appendChild(App.el('span', 'wy-hint', '💡 ' + (MAP.hint || '点画上的实物试试')));
      if (MAP.bgCredit) { foot.appendChild(App.el('span', 'wy-credit', MAP.bgCredit)); }
      el.appendChild(foot);

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
      S.selZone = zone;
      S.view = 'detail';
      render();
    }

    /* ---------- 实物详情（学习卡） ---------- */
    function renderDetail(el) {
      var flat = flatObjects();
      var idx = -1;
      flat.forEach(function (it, k) { if (it.obj.char === S.sel) { idx = k; } });
      if (idx < 0) { S.view = 'map'; renderMap(el); return; }
      var zone = flat[idx].zone;
      var o = flat[idx].obj;
      var p = progress();

      var back = App.el('button', 'btn sm', '← 回到地图');
      back.onclick = function () { S.view = 'map'; S.sel = null; render(); };
      el.appendChild(back);

      var card = App.el('div', 'wy-card');
      var big = App.el('div', 'wy-card-form');
      if (!App.glyphSvg(o.char)) {
        big.appendChild(App.el('div', 'wy-glyph-none', '（缺字形）'));
      } else {
        var sv = svgEl('svg');
        sv.setAttribute('viewBox', '0 0 ' + CANVAS + ' ' + CANVAS);
        sv.setAttribute('class', 'wy-big');
        sv.setAttribute('aria-hidden', 'true');
        sv.innerHTML = App.glyphSvg(o.char, 'currentColor');
        big.appendChild(sv);
      }
      card.appendChild(big);

      var info = App.el('div', 'wy-card-info');
      var row = App.el('div', 'wy-card-row');
      row.appendChild(App.el('span', 'wy-card-char', o.char));
      row.appendChild(App.el('span', 'wy-card-zone', zone.name || ''));
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

      /* 接着认：给前后各几个，顺着看下去 */
      var near = [];
      for (var d = 1; d <= 4 && near.length < 8; d++) {
        var a = flat[(idx + d) % flat.length];
        var b = flat[(idx - d + flat.length) % flat.length];
        if (a && a.obj.char !== o.char && near.indexOf(a) < 0) { near.push(a); }
        if (b && b.obj.char !== o.char && near.indexOf(b) < 0 && near.length < 8) { near.push(b); }
      }
      if (near.length) {
        var more = App.el('div', 'wy-more');
        more.appendChild(App.el('div', 'wy-more-title', '接着认'));
        var strip = App.el('div', 'wy-more-strip');
        near.forEach(function (it2) {
          var bb = App.el('button', 'wy-mini' +
            (isSeen(p, it2.zone.id, it2.obj.char) ? ' seen' : ''));
          var mg = svgEl('svg');
          mg.setAttribute('viewBox', '0 0 ' + CANVAS + ' ' + CANVAS);
          mg.setAttribute('class', 'wy-mini-glyph');
          if (App.glyphSvg(it2.obj.char)) {
            mg.innerHTML = App.glyphSvg(it2.obj.char, 'currentColor');
          }
          bb.appendChild(mg);
          bb.appendChild(App.el('span', 'wy-mini-name', it2.obj.char));
          bb.title = it2.obj.meaning || it2.obj.char;
          bb.onclick = function () {
            markSeen(it2.zone.id, it2.obj.char);
            S.sel = it2.obj.char;
            S.selZone = it2.zone;
            render();
          };
          strip.appendChild(bb);
        });
        more.appendChild(strip);
        el.appendChild(more);
      }

      var bar = App.el('div', 'wy-side');
      var prev = flat[(idx - 1 + flat.length) % flat.length];
      var next = flat[(idx + 1) % flat.length];
      var a1 = App.el('button', 'btn sm', '← 上一个（' + prev.obj.char + '）');
      a1.onclick = function () {
        markSeen(prev.zone.id, prev.obj.char);
        S.sel = prev.obj.char; S.selZone = prev.zone; render();
      };
      var b1 = App.el('button', 'btn sm', '下一个（' + next.obj.char + '）→');
      b1.onclick = function () {
        markSeen(next.zone.id, next.obj.char);
        S.sel = next.obj.char; S.selZone = next.zone; render();
      };
      bar.appendChild(a1);
      bar.appendChild(b1);
      el.appendChild(bar);
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
      (MAP.quiz.zones || []).forEach(function (z) {
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

    render();
  }

  var S = { view: 'map', sel: null, selZone: null, showHot: false };

  function unmount() { S.view = 'map'; S.sel = null; S.selZone = null; S.showHot = false; }

  App.modes.register({
    id: 'wangyi-map',
    name: '殷商王邑',
    tagline: '点画上的实物，认甲骨文',
    desc: '一张三千年前的王邑图卷。山川、田亩、城邑、牲畜、器物都画在上面，'
        + '点哪一样东西，就看古人把它画成什么字。认过的会留一枚小印记。',
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
