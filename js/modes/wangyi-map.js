/* ============================================================
   字趣 · 玩法模块：殷商王邑（图卷 · 点亮 · 构字）

   玩法主线：
     整幅画初始是【灰的】→ 点画上的实物 → 进入【构字界面】
     上面是甲骨文原字，下面是打散的笔画，拖到正确位置拼出来
     → 拼成后那一块地方在地图上【亮起来】

   点亮怎么做的（不用切图、不用预做遮罩）：
     底层：同一张图，CSS 灰度化
     上层：原图，用 <mask> 只露出「已完成」那些字的圆形区域
     完成一个字 = 往 mask 里加一个白色圆 → 那块就亮了
     圆心/半径直接取热区的 x,y,r，所以「亮的地方」就是「点的地方」。

   笔画来源：
     glyph-parts.json 里每个字按 M 起点拆成 1~17 笔（山 1 笔、鱼 16 笔），
     每笔带画布坐标包围盒。部件池里按自身包围盒单独显示；
     拖回目标时用同一套画布坐标就位——所以是「拼回原字」，不是随便贴。

   数据全在 js/core/levels.json，代码不写死任何字表。
   ============================================================ */
(function (App) {
  'use strict';

  var MAP = (App.levels && App.levels.map) || null;
  var STORE_KEY = 'wangyi';
  var SVGNS = 'http://www.w3.org/2000/svg';
  var CV = 100;                 /* 字形画布 */
  var uid = 0;

  /* ---------- 完成记录 ----------
     { done: { zoneId: [已拼成的字, ...] } } */
  function progress() {
    var p = App.store.get(STORE_KEY, null);
    if (!p || typeof p !== 'object') p = {};
    if (!p.done || typeof p.done !== 'object') {
      /* 兼容早期只有 seen 的记录 */
      p.done = p.seen && typeof p.seen === 'object' ? p.seen : {};
    }
    return p;
  }
  function saveProgress(p) { App.store.set(STORE_KEY, p); }
  function doneList(p, zoneId) { return p.done[zoneId] || []; }
  function isDone(p, zoneId, ch) { return doneList(p, zoneId).indexOf(ch) >= 0; }
  function markDone(zoneId, ch) {
    var p = progress();
    if (!p.done[zoneId]) { p.done[zoneId] = []; }
    if (p.done[zoneId].indexOf(ch) < 0) { p.done[zoneId].push(ch); saveProgress(p); }
    return p;
  }
  function doneTotal(p) {
    var n = 0;
    (MAP.zones || []).forEach(function (z) { n += doneList(p, z.id).length; });
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
    S.zone = null;
    S.showHot = false;
    S.placed = [];      /* 已就位的笔画序号 */
    S.pool = [];        /* 部件池顺序（打散） */
    S.drag = null;

    var root = App.el('div', 'scene wangyi');
    host.appendChild(root);

    if (!MAP || !MAP.zones || !MAP.zones.length) {
      root.appendChild(App.el('p', 'lead', '地图数据缺失（js/core/levels.json）。'));
      return;
    }

    function render() {
      App.clearNode(root);
      if (S.view === 'compose' && S.sel) { renderCompose(root); return; }
      if (S.view === 'done' && S.sel) { renderDone(root); return; }
      if (S.view === 'quiz') { renderQuizEntry(root); return; }
      renderMap(root);
    }

    /* ---------- 地图（灰底 + 点亮层 + 隐形热区） ---------- */
    function renderMap(el) {
      var p = progress();
      var total = objectTotal();
      var dn = doneTotal(p);

      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', MAP.name));
      head.appendChild(App.el('span', 'wy-sub', MAP.subtitle || ''));
      el.appendChild(head);

      var bar = App.el('div', 'wy-learnbar');
      bar.appendChild(App.el('span', 'wy-learnnum', dn + ' / ' + total));
      bar.appendChild(App.el('span', 'wy-learnword', '个实物已点亮'));
      var meter = App.el('span', 'wy-meter');
      var fill = App.el('i', 'wy-meter-fill');
      fill.style.width = (total ? (dn / total * 100) : 0) + '%';
      meter.appendChild(fill);
      bar.appendChild(meter);

      var toggle = App.el('button', 'btn sm wy-hotbtn' + (S.showHot ? ' on' : ''),
        S.showHot ? '隐藏可点处' : '显示可点处（' + total + ' 处）');
      toggle.onclick = function () { S.showHot = !S.showHot; render(); };
      bar.appendChild(toggle);
      el.appendChild(bar);

      var vb = String(MAP.viewBox || '0 0 1800 907').split(/\s+/);
      var VW = +vb[2] || 1800;
      var VH = +vb[3] || 907;
      var myId = 'wy' + (++uid);

      var wrap = App.el('div', 'wy-map' + (S.showHot ? ' show-hots' : ''));
      var svg = svgEl('svg');
      svg.setAttribute('class', 'wy-omap');
      svg.setAttribute('viewBox', MAP.viewBox || '0 0 1800 907');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', MAP.name + '：点画上的实物认甲骨文');

      /* defs：柔边渐变 + 点亮遮罩（遮罩内容 = 已完成字的圆） */
      var defs = svgEl('defs');
      var grad = svgEl('radialGradient');
      grad.setAttribute('id', myId + 'fade');
      [['55%', '#fff'], ['100%', '#000']].forEach(function (st) {
        var s = svgEl('stop');
        s.setAttribute('offset', st[0]);
        s.setAttribute('stop-color', st[1]);
        grad.appendChild(s);
      });
      defs.appendChild(grad);

      var mask = svgEl('mask');
      mask.setAttribute('id', myId + 'lit');
      var mrect = svgEl('rect');
      mrect.setAttribute('x', 0); mrect.setAttribute('y', 0);
      mrect.setAttribute('width', VW); mrect.setAttribute('height', VH);
      mrect.setAttribute('fill', '#000');
      mask.appendChild(mrect);
      (MAP.zones || []).forEach(function (z) {
        (z.objects || []).forEach(function (o) {
          if (!isDone(p, z.id, o.char)) { return; }
          var c = svgEl('circle');
          c.setAttribute('cx', o.x);
          c.setAttribute('cy', o.y);
          c.setAttribute('r', (o.r || 30) * 1.35);
          c.setAttribute('fill', 'url(#' + myId + 'fade)');
          mask.appendChild(c);
        });
      });
      defs.appendChild(mask);
      svg.appendChild(defs);

      /* 底层：灰度图 */
      var imgDim = svgEl('image');
      imgDim.setAttribute('class', 'wy-bg-dim');
      imgDim.setAttribute('x', 0); imgDim.setAttribute('y', 0);
      imgDim.setAttribute('width', VW); imgDim.setAttribute('height', VH);
      imgDim.setAttribute('preserveAspectRatio', 'xMidYMid slice');
      imgDim.setAttribute('href', MAP.bgImage);
      svg.appendChild(imgDim);

      /* 上层：彩色原图，只在遮罩里露出——即「已点亮」的那些地方 */
      var imgLit = svgEl('image');
      imgLit.setAttribute('class', 'wy-bg-lit');
      imgLit.setAttribute('x', 0); imgLit.setAttribute('y', 0);
      imgLit.setAttribute('width', VW); imgLit.setAttribute('height', VH);
      imgLit.setAttribute('preserveAspectRatio', 'xMidYMid slice');
      imgLit.setAttribute('href', MAP.bgImage);
      imgLit.setAttribute('mask', 'url(#' + myId + 'lit)');
      svg.appendChild(imgLit);

      /* 隐形热区 */
      flatObjects().forEach(function (it) {
        var z = it.zone;
        var o = it.obj;
        var r = o.r || 30;
        var got = isDone(p, z.id, o.char);

        var g = svgEl('g');
        g.setAttribute('class', 'wy-spot' + (got ? ' seen' : ''));
        g.setAttribute('transform', 'translate(' + o.x + ',' + o.y + ')');
        g.setAttribute('tabindex', '0');
        g.setAttribute('role', 'button');
        g.setAttribute('aria-label', o.char + '，' + (o.meaning || '') +
          (got ? '（已点亮）' : ''));

        var hit = svgEl('circle');
        hit.setAttribute('r', r);
        hit.setAttribute('class', 'wy-hot');
        g.appendChild(hit);

        var ring = svgEl('circle');
        ring.setAttribute('r', r);
        ring.setAttribute('class', 'wy-ring');
        g.appendChild(ring);

        /* 悬停：浮出该字的甲骨字形小牌 */
        var pop = svgEl('g');
        pop.setAttribute('class', 'wy-pop');
        var pbg = svgEl('circle');
        pbg.setAttribute('r', 28);
        pbg.setAttribute('class', 'wy-pop-bg');
        pop.appendChild(pbg);
        var form = svgEl('g');
        form.setAttribute('class', 'wy-pop-form');
        form.setAttribute('transform', 'translate(-20,-22) scale(0.4)');
        if (App.hasGlyph(o.char)) { form.innerHTML = App.glyphSvg(o.char, 'currentColor'); }
        pop.appendChild(form);
        var lab = svgEl('text');
        lab.setAttribute('class', 'wy-pop-label');
        lab.setAttribute('text-anchor', 'middle');
        lab.setAttribute('y', 46);
        lab.textContent = o.char;
        pop.appendChild(lab);
        g.appendChild(pop);

        function pick() {
          S.sel = o.char;
          S.zone = z;
          S.view = 'compose';
          S.placed = [];
          S.pool = shuffle(range(App.glyphStrokeCount(o.char)));
          render();
        }
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
      var modes = App.el('button', 'btn sm', '甲骨构字（原有玩法）');
      modes.onclick = function () { ctx.nav.modes(); };
      side.appendChild(modes);

      /* 一键点亮：演示/展示用。地图初始是全部未点亮的灰图，
         按这个把 61 处一次点亮。不做二次确认——演示时弹窗碍事，
         而且「重置」就在旁边，随时能退回灰图。 */
      var lightAll = App.el('button', 'btn sm', '一键点亮（61 处）');
      lightAll.onclick = function () {
        var p = progress();
        (MAP.zones || []).forEach(function (z) {
          if (!p.done[z.id]) { p.done[z.id] = []; }
          (z.objects || []).forEach(function (o) {
            if (p.done[z.id].indexOf(o.char) < 0) { p.done[z.id].push(o.char); }
          });
        });
        saveProgress(p);
        render();
      };
      side.appendChild(lightAll);

      var reset = App.el('button', 'btn sm', '重置点亮记录');
      reset.onclick = function () {
        if (!window.confirm('确定清空点亮记录？整幅画会重新变灰。')) return;
        App.store.del(STORE_KEY);
        render();
      };
      side.appendChild(reset);
      el.appendChild(side);
    }

    /* ---------- 构字界面：上原文、下部件、拖拽拼合 ---------- */
    function renderCompose(el) {
      var ch = S.sel;
      var zone = S.zone;
      var strokes = App.glyphStrokes(ch);
      var n = strokes.length;
      var p = progress();
      var already = zone && isDone(p, zone.id, ch);

      var back = App.el('button', 'btn sm', '← 回到地图');
      back.onclick = function () { S.view = 'map'; render(); };
      el.appendChild(back);

      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', '甲骨文「' + ch + '」'));
      head.appendChild(App.el('span', 'wy-cell-rank', n + ' 笔'));
      el.appendChild(head);

      /* 上：甲骨文原字（参照） */
      var refBox = App.el('div', 'wy-ref');
      refBox.appendChild(App.el('div', 'wy-ref-label', '甲骨文原字'));
      var refSvg = svgEl('svg');
      refSvg.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      refSvg.setAttribute('class', 'wy-ref-glyph');
      if (App.hasGlyph(ch)) { refSvg.innerHTML = App.glyphSvg(ch, 'currentColor'); }
      refBox.appendChild(refSvg);
      var refInfo = App.el('div', 'wy-ref-info');
      refInfo.appendChild(App.el('div', 'wy-ref-mean', (S.zone && S.zone.name) || ''));
      var o0 = null;
      flatObjects().forEach(function (it) { if (it.obj.char === ch) { o0 = it.obj; } });
      refInfo.appendChild(App.el('div', 'wy-ref-desc', (o0 && o0.meaning) || ''));
      if (already) { refInfo.appendChild(App.el('div', 'wy-ref-done', '✓ 已点亮')); }
      refBox.appendChild(refInfo);
      el.appendChild(refBox);

      el.appendChild(App.el('div', 'wy-q-label',
        '把下面的笔画拖到上方的格子里，摆到正确的位置，拼出这个字'));

      /* 中：组装区（含淡淡的原字作为位置提示） */
      var stageWrap = App.el('div', 'wy-stagewrap');
      var stage = svgEl('svg');
      stage.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      stage.setAttribute('class', 'wy-stage-svg');
      stage.setAttribute('id', 'wyStage');

      var guide = svgEl('g');
      guide.setAttribute('class', 'wy-guide');
      if (App.hasGlyph(ch)) { guide.innerHTML = App.glyphSvg(ch, 'currentColor'); }
      stage.appendChild(guide);

      var placedG = svgEl('g');
      placedG.setAttribute('class', 'wy-placed');
      stage.appendChild(placedG);
      stageWrap.appendChild(stage);
      el.appendChild(stageWrap);

      /* 下：部件池 */
      var tray = App.el('div', 'wy-tray');
      tray.appendChild(App.el('div', 'wy-tray-label', '笔画（拖到上面）'));
      var pool = App.el('div', 'wy-tray-items');
      tray.appendChild(pool);
      el.appendChild(tray);

      var verdict = App.el('div', 'verdict');
      el.appendChild(verdict);

      var tbar = App.el('div', 'wy-side');
      var re = App.el('button', 'btn sm', '重摆');
      re.onclick = function () { S.placed = []; S.pool = shuffle(range(n)); render(); };
      tbar.appendChild(re);
      var skip = App.el('button', 'btn sm', '直接看释义');
      skip.onclick = function () { S.view = 'done'; render(); };
      tbar.appendChild(skip);
      el.appendChild(tbar);

      /* 画已就位的笔画 */
      function paintPlaced() {
        App.clearNode(placedG);
        S.placed.forEach(function (i) {
          var g = svgEl('g');
          g.setAttribute('class', 'wy-stroke ok');
          g.innerHTML = App.glyphStrokeSvg(ch, i, 'currentColor');
          placedG.appendChild(g);
        });
      }

      /* 部件池：每笔按自身包围盒单独显示 */
      function paintPool() {
        App.clearNode(pool);
        S.pool.forEach(function (i) {
          if (S.placed.indexOf(i) >= 0) { return; }
          var c = strokes[i].c;
          var w = Math.max(c[2] - c[0], 1e-3);
          var h = Math.max(c[3] - c[1], 1e-3);
          var pad = Math.max(w, h) * 0.35 + 2;
          var b = App.el('div', 'wy-piece');
          b.setAttribute('data-i', String(i));
          var s = svgEl('svg');
          s.setAttribute('viewBox', (c[0] - pad) + ' ' + (c[1] - pad) + ' ' +
            (w + pad * 2) + ' ' + (h + pad * 2));
          s.setAttribute('class', 'wy-piece-svg');
          s.innerHTML = App.glyphStrokeSvg(ch, i, 'currentColor');
          b.appendChild(s);
          attachDrag(b, i, s, c);
          pool.appendChild(b);
        });
        if (!pool.children.length) {
          pool.appendChild(App.el('div', 'wy-tray-empty', '部件都摆上去了'));
        }
      }

      /* 拖拽：指针事件（鼠标与触屏通用）。
         判定用「落点与这一笔应在位置的圆心距」——所以是真的要摆对地方，
         不是随便放进去就算。 */
      function attachDrag(box, idx, svgNode, c) {
        var targetX = (c[0] + c[2]) / 2;
        var targetY = (c[1] + c[3]) / 2;
        var tol = Math.max(16, Math.max(c[2] - c[0], c[3] - c[1]) * 0.55);

        function toCanvas(clientX, clientY) {
          var r = stage.getBoundingClientRect();
          return {
            x: (clientX - r.left) / r.width * CV,
            y: (clientY - r.top) / r.height * CV
          };
        }

        box.addEventListener('pointerdown', function (ev) {
          ev.preventDefault();
          box.classList.add('dragging');
          try { box.setPointerCapture(ev.pointerId); } catch (e) { /* 忽略 */ }
          S.drag = { i: idx, x: targetX, y: targetY, tol: tol };

          function move(e) {
            box.style.transform = 'translate(' + (e.clientX - ev.clientX) + 'px,' +
              (e.clientY - ev.clientY) + 'px)';
          }
          function up(e) {
            box.removeEventListener('pointermove', move);
            box.removeEventListener('pointerup', up);
            box.removeEventListener('pointercancel', up);
            box.classList.remove('dragging');
            box.style.transform = '';
            var pt = toCanvas(e.clientX, e.clientY);
            var d = Math.sqrt(Math.pow(pt.x - targetX, 2) + Math.pow(pt.y - targetY, 2));
            if (d <= tol) {
              S.placed.push(idx);
              paintPlaced();
              paintPool();
              check();
            } else {
              box.classList.add('miss');
              setTimeout(function () { box.classList.remove('miss'); }, 420);
              /* 说清"偏在哪"：只给八方向与远近档，不给落点坐标——
                 坐标就是答案，给了等于代打。
                 方向按"目标相对落点"算：dx>0 说明目标在右侧，该往右挪。 */
              var dx = targetX - pt.x, dy = targetY - pt.y;
              var hz = dx > 8 ? '右' : (dx < -8 ? '左' : '');
              var vt = dy > 8 ? '下' : (dy < -8 ? '上' : '');
              var dir = (vt + hz) || '原处附近';
              var far = d > tol * 2.2 ? '还差得比较远' : '就差一点';
              verdict.className = 'verdict no';
              verdict.textContent = '✘ 没到位——这笔该往「' + dir + '」挪（' + far +
                '）。已摆 ' + S.placed.length + ' / ' + n + ' 笔。';
            }
            S.drag = null;
          }
          box.addEventListener('pointermove', move);
          box.addEventListener('pointerup', up);
          box.addEventListener('pointercancel', up);
        });
      }

      function check() {
        if (S.placed.length < n) {
          verdict.className = 'verdict';
          verdict.textContent = '已摆 ' + S.placed.length + ' / ' + n + ' 笔';
          return;
        }
        markDone(zone.id, ch);
        verdict.className = 'verdict ok';
        verdict.textContent = '✔ 拼成了「' + ch + '」！地图上这一块亮起来了。';
        var nx = App.el('button', 'btn primary', '看看释义');
        nx.onclick = function () { S.view = 'done'; render(); };
        verdict.appendChild(nx);
      }

      paintPlaced();
      paintPool();
      if (n) {
        verdict.className = 'verdict';
        verdict.textContent = '已摆 ' + S.placed.length + ' / ' + n + ' 笔';
      } else {
        verdict.className = 'verdict no';
        verdict.textContent = '这个字没有可拆的笔画。';
      }
    }

    /* ---------- 完成卡：字形 + 今字 + 释义 ---------- */
    function renderDone(el) {
      var ch = S.sel;
      var zone = S.zone;
      var o = null;
      flatObjects().forEach(function (it) { if (it.obj.char === ch) { o = it.obj; } });

      var back = App.el('button', 'btn sm', '← 回到地图');
      back.onclick = function () { S.view = 'map'; S.sel = null; render(); };
      el.appendChild(back);

      var card = App.el('div', 'wy-card');
      var big = App.el('div', 'wy-card-form');
      var sv = svgEl('svg');
      sv.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      sv.setAttribute('class', 'wy-big');
      if (App.hasGlyph(ch)) { sv.innerHTML = App.glyphSvg(ch, 'currentColor'); }
      big.appendChild(sv);
      card.appendChild(big);

      var info = App.el('div', 'wy-card-info');
      var row = App.el('div', 'wy-card-row');
      row.appendChild(App.el('span', 'wy-card-char', ch));
      row.appendChild(App.el('span', 'wy-card-zone', (zone && zone.name) || ''));
      row.appendChild(App.el('span', 'wy-cell-rank', App.glyphStrokeCount(ch) + ' 笔'));
      info.appendChild(row);
      info.appendChild(App.el('div', 'wy-card-mean', (o && o.meaning) || ''));
      var gl = (App.glyphs && App.glyphs.parts) ? App.glyphs.parts[ch] : null;
      if (gl && gl.sourceChar && gl.sourceChar !== ch) {
        info.appendChild(App.el('div', 'wy-card-note',
          '数据集中的字形对应「' + gl.sourceChar + '」（glyphId ' + gl.glyphId + '）'));
      }
      if (gl && gl.isFallback) {
        info.appendChild(App.el('div', 'wy-card-note', '※ 数据集未收录此字，借用其形代用。'));
      }
      card.appendChild(info);
      el.appendChild(card);

      var bar = App.el('div', 'wy-side');

      /* 下一处：同区优先（本来就在这一片看），本区点完了再跨区找。
         一个都找不到说明整幅画都点亮了，就不摆这个按钮。 */
      var p0 = progress();
      var nextIt = null;
      var all = flatObjects();
      var same = all.filter(function (it) { return it.zone.id === (zone && zone.id); });
      var look = same.concat(all);
      for (var q = 0; q < look.length; q++) {
        if (!isDone(p0, look[q].zone.id, look[q].obj.char)) { nextIt = look[q]; break; }
      }
      if (nextIt) {
        var nx2 = App.el('button', 'btn primary', '下一处 →');
        nx2.onclick = function () {
          S.zone = nextIt.zone;
          S.sel = nextIt.obj.char;
          S.placed = [];
          S.pool = shuffle(range(App.glyphStrokeCount(nextIt.obj.char)));
          S.view = 'compose';
          render();
        };
        bar.appendChild(nx2);
      }

      var nxt = App.el('button', 'btn sm', '回到地图');
      nxt.onclick = function () { S.view = 'map'; S.sel = null; render(); };
      bar.appendChild(nxt);
      var again = App.el('button', 'btn sm', '再拼一次');
      again.onclick = function () {
        S.placed = []; S.pool = shuffle(range(App.glyphStrokeCount(ch)));
        S.view = 'compose'; render();
      };
      bar.appendChild(again);
      el.appendChild(bar);
    }

    /* ---------- 答题练习入口（原有玩法） ---------- */
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
          App.toast('答题玩法暂未在地图内启用，可先用「甲骨构字」。');
        };
        wrap.appendChild(b);
      });
      el.appendChild(wrap);
    }

    render();
  }

  function range(n) { var a = []; for (var i = 0; i < n; i++) { a.push(i); } return a; }
  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  var S = { view: 'map', sel: null, zone: null, showHot: false, placed: [], pool: [], drag: null };

  function unmount() {
    S.view = 'map'; S.sel = null; S.zone = null; S.showHot = false;
    S.placed = []; S.pool = []; S.drag = null;
  }

  App.modes.register({
    id: 'wangyi-map',
    name: '殷商王邑',
    tagline: '点实物、拼甲骨文、点亮地图',
    desc: '一张三千年前的王邑图卷，初始是灰的。点画上的实物，' +
        '上面给出甲骨文原字，下面给出笔画，拖到正确位置拼出来——' +
        '拼成一个字，地图上那一块就亮起来。',
    icon: '邑',
    accent: 'var(--bronze)',
    tags: ['拖拽构字', '61 个实物', '点亮地图'],
    /* 主打玩法：占满整个界面（侧栏让位、去掉内容列 900px 限宽） */
    layout: 'wide',
    minPlayers: 1, maxPlayers: 1,
    status: 'ready',
    data: { packs: [], assets: [] },
    mount: mount,
    unmount: unmount
  });

})(window.App = window.App || {});
