/* ============================================================
   字趣 · 玩法模块：殷商王邑（大地图 → 主题小地图 → 点实物学字）

   结构（对应需求「一、二、三」）：

     ① 大地图（renderWorld）
        六张新图里的大地图 `assets/level2-world.jpg` 做成整幅入口画面。
        五个区域的入口**融进地图**：一圈兆纹细环 + 一个小圆点 + 简短主题名，
        低对比、无粗边框、无硬卡片、无阴影。五区**任意顺序**都能进，不设解锁。
        某一区学完，用一层柔光把该区域点亮（不是贴一块方图，避免破坏画面）。

     ② 小地图（renderZone）
        该区的分区插画做背景，把该区每个字物按数据坐标撒成热点。
        **页面下方不放汉字列表**——认字就在图上点实物。
        点中 → 出学习卡（甲骨字形 / 释义 / 构形说明）。
        卡片关掉回到原来位置（滚动位置与缩放都保留）。

     ③ 局部放大（放大镜）
        图很大（2624×1472）缩到手机上，小物件只有几像素。
        所以点空白处会按「离得最近的热点」判定，命中后**自动放大到那个字**，
        再点一次才开卡片。身体局部（目 耳 口 止 又 足）天然极小，放大倍率更高。

   坐标空间（最容易搞错的一条，见 HANDOFF「1.5 两套坐标空间」）：

        只有一个空间：**2624 × 1472**，即六张图自己的像素空间。
        大地图的据点和每个小区热点都用它，`map.viewBox = "0 0 2624 1472"`。
        数据来自 `dev/_l2_calibrate.py`（唯一真源）→ `js/core/levels.json`
        → `js/core/_data.js`。这里不写死任何坐标。

   完成记录（沿用旧键，不清空既有存档）：

        ziqu.wangyi = { done: { zoneId: [已学的字, ...] } }
        旧版本可能还有 seen 字段，读的时候兼容，写的时候只动 done。
   ============================================================ */
(function (App) {
  'use strict';

  var MAP = (App.levels && App.levels.map) || null;
  var STORE_KEY = 'wangyi';
  var SVGNS = 'http://www.w3.org/2000/svg';
  var CV = 100;                      /* 字形画布 */

  /* 触控下限：手指最小可点直径约 44 CSS px。
     热点半径是 SVG 用户单位，会随地图缩放变小，所以实际用时按
     scale = 显示宽 / 2624 反算，保证屏幕上的命中直径不小于这个值。 */
  var TOUCH_MIN_PX = 44;

  /* 需要局部放大的字：天然极小，或与宿主（人／鹿）热区挤在一起。
     倍率按「让该字周围的 560 用户单位铺满一屏」来取。 */
  var ZOOM_HINT = {
    '目': 3.4, '口': 3.4, '耳': 3.4, '止': 3.4, '又': 3.4, '足': 3.4,
    '刀': 3.0, '斧': 3.0, '斤': 3.0, '戈': 3.0, '糸': 3.0, '卜': 3.0,
    '玉': 2.8, '贝': 2.8, '矢': 2.8, '弓': 2.6,
    '米': 2.6, '屮': 2.6, '隹': 2.6, '石': 2.4, '水': 2.4, '泉': 2.4
  };

  /* 状态：
     view  map | zone
     zone  当前分区
     sel   当前打开学习卡的 [字]
     lens  放大镜状态 { char, x, y, z } 或 null
     showHot 是否显式标出所有可点处
     scroll / zoom 记住小地图的视口，卡片关掉能回到原位置
     flow  构字流程的临时状态 */
  var S = {
    view: 'map', zone: null, sel: null, lens: null, showHot: false,
    scroll: { left: 0, top: 0 }, zoom: 1,
    flow: null, drag: null
  };

  function svgEl(tag) { return document.createElementNS(SVGNS, tag); }
  function uid() { return 'wy' + (uid.n = (uid.n || 0) + 1); }

  /* ============================================================
     完成记录
     ============================================================ */
  function progress() {
    var p = App.store.get(STORE_KEY, null);
    if (!p || typeof p !== 'object') { p = {}; }
    if (!p.done || typeof p.done !== 'object') {
      p.done = (p.seen && typeof p.seen === 'object') ? p.seen : {};
    }
    return p;
  }
  function save(p) { App.store.set(STORE_KEY, p); }
  function doneList(p, zid) { return p.done[zid] || []; }
  function isDone(p, zid, ch) { return doneList(p, zid).indexOf(ch) >= 0; }
  function markDone(zid, ch) {
    var p = progress();
    if (!p.done[zid]) { p.done[zid] = []; }
    if (p.done[zid].indexOf(ch) < 0) { p.done[zid].push(ch); save(p); }
    return p;
  }
  function zoneStat(p, z) {
    var total = (z.objects || []).length;
    var done = (z.objects || []).filter(function (o) { return isDone(p, z.id, o.char); }).length;
    return { total: total, done: done, clear: total > 0 && done >= total };
  }
  function worldStat(p) {
    var zones = (MAP && MAP.zones) || [];
    var total = 0, done = 0, clear = 0;
    zones.forEach(function (z) {
      var s = zoneStat(p, z);
      total += s.total; done += s.done;
      if (s.clear) { clear += 1; }
    });
    return { zones: zones.length, total: total, done: done, clear: clear };
  }

  /* ============================================================
     挂载
     ============================================================ */
  function mount(host) {
    S.view = 'map'; S.zone = null; S.sel = null; S.lens = null;
    S.showHot = false; S.scroll = { left: 0, top: 0 }; S.zoom = 1;
    S.flow = null; S.drag = null;

    var root = App.el('div', 'scene wangyi');
    host.appendChild(root);

    if (!MAP || !MAP.zones || !MAP.zones.length) {
      root.appendChild(App.el('p', 'lead', '地图数据缺失（js/core/levels.json）。'));
      return;
    }

    function render() {
      App.clearNode(root);
      if (S.view === 'zone' && S.zone) { renderZone(root); return; }
      renderWorld(root);
    }

    /* ----------------------------------------------------------
       ① 大地图：唯一选图入口
       ---------------------------------------------------------- */
    function renderWorld(el) {
      var p = progress();
      var st = worldStat(p);

      var head = App.el('header', 'wy2-head');
      var copy = App.el('div', 'wy2-head-copy');
      copy.appendChild(App.el('p', 'wy2-kicker', '第二关 · 殷商王邑'));
      copy.appendChild(App.el('h2', 'wy2-title', '五片王邑，点一处进去'));
      copy.appendChild(App.el('p', 'wy2-lead',
        '这是一座三千年前的王邑。五片区域任意顺序进入：点图中的实物认甲骨文，认得的字就记在这一片名下。一片学完，这一片就亮起来。'));
      head.appendChild(copy);

      var meter = App.el('div', 'wy2-head-meter');
      var mline = App.el('p', 'wy2-meter-line');
      mline.appendChild(App.el('strong', null, st.clear + ' / ' + st.zones));
      mline.appendChild(App.el('span', null, ' 片已点亮'));
      meter.appendChild(mline);
      var bar = App.el('span', 'wy2-meter');
      var fill = App.el('i', 'wy2-meter-fill');
      fill.style.width = (st.zones ? st.clear / st.zones * 100 : 0) + '%';
      bar.appendChild(fill);
      meter.appendChild(bar);
      meter.appendChild(App.el('p', 'wy2-meter-words', st.done + ' / ' + st.total + ' 个字已学'));
      head.appendChild(meter);
      el.appendChild(head);

      /* 地图本体：位置百分比全部以**图片区域**为基准，
         所以图片外侧的 letterbox 不会让据点漂移。 */
      var board = App.el('div', 'wy2-board');
      var art = App.el('div', 'wy2-board-art');
      art.style.backgroundImage = 'url("' + (MAP.worldImage || MAP.bgImage) + '")';
      art.setAttribute('role', 'img');
      art.setAttribute('aria-label',
        '殷商王邑大地图，其上标有五个可进入的主题区域：天象、山川、草木、禽兽虫鱼、人居器物');
      var layer = App.el('div', 'wy2-board-layer');
      art.appendChild(layer);

      var pct = function (v, total) { return (v / total * 100) + '%'; };
      var AX = 2624, AY = 1472;

      (MAP.zones || []).forEach(function (z, i) {
        var w = z.world || { x: AX / 2, y: AY / 2, r: 300 };
        var s = zoneStat(p, z);

        /* 区域点亮：一层柔光，不是贴一块方图——贴方图会在地图上切出硬边 */
        var glow = App.el('span', 'wy2-glow' + (s.clear ? ' on' : '') + (s.done ? ' partial' : ''));
        glow.style.left = pct(w.x, AX);
        glow.style.top = pct(w.y, AY);
        glow.style.width = pct(w.r * 2, AX);
        glow.style.height = pct(w.r * 2, AY);
        layer.appendChild(glow);

        var pin = App.el('button', 'wy2-pin' + (s.clear ? ' lit' : '')
          + (w.x > AX * 0.62 ? ' flip' : ''));
        pin.type = 'button';
        pin.style.left = pct(w.x, AX);
        pin.style.top = pct(w.y, AY);
        pin.appendChild(App.el('span', 'wy2-pin-ring', ('0' + (i + 1)).slice(-2)));
        var txt = App.el('span', 'wy2-pin-txt');
        txt.appendChild(App.el('b', null, z.name));
        txt.appendChild(App.el('span', null,
          s.clear ? '已点亮' : (s.done ? s.done + ' / ' + s.total : s.total + ' 个字')));
        pin.appendChild(txt);
        pin.setAttribute('aria-label',
          '进入' + z.name + '（' + s.done + ' / ' + s.total + ' 个字已学）');
        pin.onclick = function () { enterZone(z); };
        layer.appendChild(pin);
      });

      board.appendChild(art);
      el.appendChild(board);

      /* 龟宝只做轻向导：占一行文字位，绝不压在地图上 */
      var guide = App.el('aside', 'wy2-guide');
      var mascot = App.el('img', 'wy2-guide-mascot');
      mascot.src = 'assets/guibao-side.png';
      mascot.alt = '';
      mascot.setAttribute('aria-hidden', 'true');
      guide.appendChild(mascot);
      var gcopy = App.el('div', 'wy2-guide-copy');
      if (st.clear >= st.zones && st.zones) {
        gcopy.appendChild(App.el('b', null, '五片都亮了'));
        gcopy.appendChild(App.el('span', null, '王邑全图复明。想再看一遍，随时点回去。'));
      } else if (st.done === 0) {
        gcopy.appendChild(App.el('b', null, '龟宝：先挑一片顺眼的'));
        gcopy.appendChild(App.el('span', null, '五个区域都能进。进去后点图上看得见的东西。'));
      } else {
        gcopy.appendChild(App.el('b', null, '龟宝：还差 ' + (st.total - st.done) + ' 个字'));
        gcopy.appendChild(App.el('span', null,
          '已点亮 ' + st.clear + ' 片。点地图上还暗着的地方，继续认。'));
      }
      guide.appendChild(gcopy);
      var reset = App.el('button', 'wy2-reset', '重置本关进度');
      reset.type = 'button';
      reset.onclick = function () {
        if (!window.confirm('重置第二关的学习记录？其它两关的进度不受影响。')) { return; }
        App.store.del(STORE_KEY);
        render();
      };
      guide.appendChild(reset);
      el.appendChild(guide);

      var credit = App.el('p', 'wy2-credit',
        (MAP.bgCredit || '') + '　字形数据：Oracle Bone Glyphs v0.3（Li & Bian，CC BY 4.0）。');
      el.appendChild(credit);
    }

    function enterZone(z) {
      S.zone = z; S.view = 'zone'; S.sel = null; S.lens = null;
      S.showHot = false; S.zoom = 1; S.scroll = { left: 0, top: 0 };
      S.flow = null;
      render();
    }
    function backToWorld() {
      S.view = 'map'; S.zone = null; S.sel = null; S.lens = null; S.flow = null;
      render();
    }
    function redrawZone() {
      /* 只重画小地图这一屏，保留 S.scroll / S.zoom */
      App.clearNode(root);
      renderZone(root);
    }

    /* ----------------------------------------------------------
       ② 小地图：点实物学字
       ---------------------------------------------------------- */
    function renderZone(el) {
      var p = progress();
      var z = S.zone;
      var s = zoneStat(p, z);
      var AX = 2624, AY = 1472;

      /* 顶栏：返回 + 片名 + 进度。做得薄，把纵向空间留给地图。 */
      var top = App.el('header', 'wy2-zone-top');
      var back = App.el('button', 'btn sm wy2-back', '← 大地图');
      back.type = 'button';
      back.onclick = backToWorld;
      top.appendChild(back);

      var zhead = App.el('div', 'wy2-zone-head');
      zhead.appendChild(App.el('b', null, z.name));
      zhead.appendChild(App.el('span', null,
        s.clear ? '这一片已学完 · 大地图已点亮'
                : '已学 ' + s.done + ' / ' + s.total
                  + ' · 点图上看得见的实物，点中会放大'));
      top.appendChild(zhead);

      var zbar = App.el('span', 'wy2-zone-meter');
      var zfill = App.el('i', 'wy2-zone-fill');
      zfill.style.width = (s.total ? s.done / s.total * 100 : 0) + '%';
      zbar.appendChild(zfill);
      top.appendChild(zbar);

      /* 工具：显示/隐藏可点处（学习状态）、放大复位。
         「已学」状态也要清楚但克制——所以用**小小的印记**而不是大勾。 */
      var tools = App.el('div', 'wy2-tools');
      var hotBtn = App.el('button', 'btn sm wy2-tool' + (S.showHot ? ' on' : ''),
        S.showHot ? '收起提示' : '标出可点处');
      hotBtn.type = 'button';
      hotBtn.onclick = function () { S.showHot = !S.showHot; redrawZone(); };
      tools.appendChild(hotBtn);
      if (S.zoom > 1) {
        var zBtn = App.el('button', 'btn sm wy2-tool', '缩回全景');
        zBtn.type = 'button';
        zBtn.onclick = function () { setZoom(1, null); };
        tools.appendChild(zBtn);
      }
      top.appendChild(tools);
      el.appendChild(top);

      /* 学习卡会盖在地图上方，所以先建地图，卡片挂到 el 最后 */
      var viewport = App.el('div', 'wy2-viewport' + (S.showHot ? ' show-hots' : ''));
      var stage = App.el('div', 'wy2-stage');
      var img = App.el('img', 'wy2-art');
      img.src = z.art || MAP.worldImage || MAP.bgImage;
      img.alt = z.name + '：' + (z.note || '主题小地图') + '（点图上的实物可以认甲骨文）';
      img.draggable = false;
      stage.appendChild(img);

      var svg = svgEl('svg');
      svg.setAttribute('class', 'wy2-hotspots');
      svg.setAttribute('viewBox', '0 0 ' + AX + ' ' + AY);
      svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      svg.setAttribute('aria-label', z.name + ' · ' + (z.objects || []).length + ' 个可点实物');

      var objs = (z.objects || []).map(function (o, i) {
        return { o: o, i: i, done: isDone(p, z.id, o.char) };
      });

      objs.forEach(function (it) {
        var o = it.o;
        var g = svgEl('g');
        g.setAttribute('class', 'wy2-spot' + (it.done ? ' done' : '')
          + (S.lens && S.lens.char === o.char ? ' focus' : ''));
        g.setAttribute('transform', 'translate(' + o.x + ',' + o.y + ')');

        var hit = svgEl('circle');
        hit.setAttribute('r', o.r || 70);
        hit.setAttribute('class', 'wy2-hit');
        g.appendChild(hit);

        var ring = svgEl('circle');
        ring.setAttribute('r', o.r || 70);
        ring.setAttribute('class', 'wy2-ring');
        g.appendChild(ring);

        if (it.done) {
          /* 已学：一枚小小的朱砂印记。克制，但看得见。 */
          var seal = svgEl('g');
          seal.setAttribute('class', 'wy2-seal');
          var sc = svgEl('circle');
          sc.setAttribute('r', Math.max(16, (o.r || 70) * 0.22));
          sc.setAttribute('class', 'wy2-seal-bg');
          seal.appendChild(sc);
          var st = svgEl('text');
          st.setAttribute('class', 'wy2-seal-text');
          st.setAttribute('text-anchor', 'middle');
          st.setAttribute('dominant-baseline', 'central');
          st.textContent = o.char;
          seal.appendChild(st);
          g.appendChild(seal);
        }
        svg.appendChild(g);
      });

      stage.appendChild(svg);
      viewport.appendChild(stage);
      el.appendChild(viewport);

      if (!objs.length) {
        el.appendChild(App.el('p', 'lead', '这一片还没有学习点。'));
        return;
      }

      /* ---- 视口与放大 ----
         stage 的宽高都写成像素：图片按 100%/100% 拉伸，
         svg 也显式给同样的像素宽高 + meet，于是两者永远严丝合缝。
         这样「放大后热点还在实物上」不需要任何额外换算。 */
      function applyZoom(anchor) {
        /* 每次都从 DOM 现取视口：setZoom 会整屏重画，闭包里的旧节点已经脱离文档，
           继续用它会量到 0 宽高（那正是"缩回全景后 scrollTop 卡在 84"的根因）。 */
        var vp = root.querySelector('.wy2-viewport');
        if (!vp) { return; }
        viewport = vp;
        var zf = S.zoom;
        var vw = vp.clientWidth || 900;
        var vh = vp.clientHeight || 500;
        var w = Math.round(vw * zf);
        var h = Math.round(w * AY / AX);
        if (h < vh * zf) {          /* 极宽的图：以高度为准，避免上下留白过多 */
          h = Math.round(vh * zf);
          w = Math.round(h * AX / AY);
        }
        if (anchor === undefined) { anchor = S.anchor; }
        stage.style.width = w + 'px';
        stage.style.height = h + 'px';
        svg.setAttribute('width', String(w));
        svg.setAttribute('height', String(h));
        if (anchor) {
          var tx = anchor.x / AX * w;
          var ty = anchor.y / AY * h;
          S.scroll.left = clamp(tx - vw / 2, 0, Math.max(0, w - vw));
          S.scroll.top = clamp(ty - vh / 2, 0, Math.max(0, h - vh));
        } else {
          S.scroll.left = 0;
          S.scroll.top = 0;
        }
        vp.scrollLeft = S.scroll.left;
        vp.scrollTop = S.scroll.top;
      }
      function setZoom(zf, anchor) {
        S.zoom = Math.max(1, Math.min(4, zf));
        S.anchor = anchor || (S.lens ? { x: S.lens.x, y: S.lens.y } : null);
        if (S.zoom <= 1.02) { S.zoom = 1; S.anchor = null; S.lens = null; }
        redrawZone();
        /* 重画后 viewport 是新节点：必须**先定尺寸、再落滚动**，
           否则会把上一轮的旧 scrollTop 落到新节点上（会 scrollTop=84 却无处可滚）。
           缩回全景时锚点为空，applyZoom 会把滚动归零。 */
        requestAnimationFrame(function () {
          var vp = root.querySelector('.wy2-viewport');
          if (!vp) { return; }
          viewport = vp;
          applyZoom(S.anchor);
        });
      }
      /* 点击判定：最近者优先 ----
         手机上图缩得很小，小物件只有几像素，逐像素去点不现实。
         所以按落点找**最近的热点**（超出容忍距离就不认），
         命中后自动放大到它，再点一次才开卡片。 */
      window.__wyDbg = window.__wyDbg || { taps: [], picks: [] };
      function pickAt(clientX, clientY) {
        var r = svg.getBoundingClientRect();
        if (!r.width || !r.height) { return null; }
        /* svg 是 meet 的：图片区域可能比 svg 框小，先算出真实图片区域 */
        var scale = Math.min(r.width / AX, r.height / AY);
        var dispW = AX * scale, dispH = AY * scale;
        var offX = r.left + (r.width - dispW) / 2;
        var offY = r.top + (r.height - dispH) / 2;
        var ux = (clientX - offX) / scale;
        var uy = (clientY - offY) / scale;
        if (ux < -40 || uy < -40 || ux > AX + 40 || uy > AY + 40) { return null; }

        /* 手指容差：把 44px 换成用户单位，并给一点余量 */
        var tolPx = 26;
        var tol = tolPx / scale;
        var best = null, bd = Infinity;
        objs.forEach(function (it) {
          var o = it.o;
          var d = Math.sqrt(Math.pow(o.x - ux, 2) + Math.pow(o.y - uy, 2));
          var reach = Math.max(o.r || 70, tol);
          if (d <= reach && d < bd) { bd = d; best = it; }
        });
        return best;
      }

      function onTap(ev) {
        var it = pickAt(ev.clientX, ev.clientY);
        if (!it) {
          if (window.__wyDbg) {
            window.__wyDbg.taps.push({ x: Math.round(ev.clientX), y: Math.round(ev.clientY),
              hit: null, zoom: S.zoom, lens: S.lens ? S.lens.char : null });
          }
          return;
        }
        var o = it.o;
        var sameAsLens = !!(S.lens && S.lens.char === o.char);
        if (window.__wyDbg) {
          window.__wyDbg.taps.push({
            x: Math.round(ev.clientX), y: Math.round(ev.clientY),
            hit: o.char, zoom: S.zoom, lens: S.lens ? S.lens.char : null,
            same: sameAsLens, willCard: !!(S.zoom > 1 && sameAsLens)
          });
        }
        /* 已经放大到它了：这一次点就是「打开学习卡」 */
        if (S.zoom > 1 && sameAsLens) {
          try {
            openCard(it);
            if (window.__wyDbg) { window.__wyDbg.taps[window.__wyDbg.taps.length - 1].ok = 1; }
          } catch (err) {
            if (window.__wyDbg) {
              window.__wyDbg.taps[window.__wyDbg.taps.length - 1].ok = 0;
              window.__wyDbg.err = String((err && err.stack) || err);
            }
          }
          return;
        }
        var zf = ZOOM_HINT[o.char] || 2.6;
        S.lens = { char: o.char, x: o.x, y: o.y };
        setZoom(zf, { x: o.x, y: o.y });
      }

      /* 用 pointerup 而不是 click：手机上拖动图像后不会误触 */
      var downAt = null;
      viewport.addEventListener('pointerdown', function (ev) {
        downAt = { x: ev.clientX, y: ev.clientY, t: Date.now() };
      });
      viewport.addEventListener('pointerup', function (ev) {
        if (!downAt) { return; }
        var moved = Math.abs(ev.clientX - downAt.x) + Math.abs(ev.clientY - downAt.y);
        var quick = Date.now() - downAt.t < 700;
        downAt = null;
        if (moved > 12 || !quick) { return; }   /* 是拖动/长按，不算点选 */
        onTap(ev);
      });
      viewport.addEventListener('scroll', function () {
        S.scroll.left = viewport.scrollLeft;
        S.scroll.top = viewport.scrollTop;
      });

      /* ---- 学习卡 ---- */
      function openCard(it) {
        S.sel = it.o.char;
        buildCard(it);
      }
      function buildCard(it) {
        S.sel = it.o.char;
        var prev = root.querySelector('.wy2-card-wrap');
        if (prev) { prev.parentNode.removeChild(prev); }
        var wrap = App.el('div', 'wy2-card-wrap');
        var card = App.el('div', 'wy2-card');
        card.setAttribute('role', 'dialog');
        card.setAttribute('aria-modal', 'true');
        card.setAttribute('aria-label', it.o.char + ' 的学习卡');

        var closeX = App.el('button', 'wy2-card-x', '✕');
        closeX.type = 'button';
        closeX.setAttribute('aria-label', '关闭学习卡');
        closeX.onclick = closeCard;
        card.appendChild(closeX);

        var form = App.el('div', 'wy2-card-form');
        var g = svgEl('svg');
        g.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
        g.setAttribute('class', 'wy2-card-glyph');
        if (App.hasGlyph(it.o.char)) { g.innerHTML = App.glyphSvg(it.o.char, 'currentColor'); }
        form.appendChild(g);
        form.appendChild(App.el('span', 'wy2-card-zone', z.name));
        if (it.done) { form.appendChild(App.el('span', 'wy2-card-done', '已学')); }
        card.appendChild(form);

        var info = App.el('div', 'wy2-card-info');
        var row = App.el('div', 'wy2-card-row');
        row.appendChild(App.el('b', 'wy2-card-char', it.o.char));
        row.appendChild(App.el('span', 'wy2-card-kind', kindOf(it.o.char)));
        info.appendChild(row);
        info.appendChild(App.el('p', 'wy2-card-mean', it.o.meaning || ''));
        if (it.o.form) {
          info.appendChild(App.el('p', 'wy2-card-form-note', it.o.form));
        }
        var gl = (App.glyphs && App.glyphs.parts) ? App.glyphs.parts[it.o.char] : null;
        if (gl && gl.sourceChar && gl.sourceChar !== it.o.char) {
          info.appendChild(App.el('p', 'wy2-card-src',
            '数据集中的字形对应「' + gl.sourceChar + '」（glyphId ' + gl.glyphId + '）'));
        }
        if (gl && gl.isFallback) {
          info.appendChild(App.el('p', 'wy2-card-src', '※ 数据集未收录此字，借用其形代用。'));
        }

        var acts = App.el('div', 'wy2-card-acts');
        var learn = App.el('button', 'btn primary', it.done ? '再练一次笔画' : '练一练：把笔画拼回去');
        learn.type = 'button';
        learn.onclick = function () { startFlow(it); };
        acts.appendChild(learn);
        var later = App.el('button', 'btn sm', '先看别的');
        later.type = 'button';
        later.onclick = closeCard;
        acts.appendChild(later);
        info.appendChild(acts);
        card.appendChild(info);

        wrap.appendChild(card);
        wrap.onclick = function (ev) { if (ev.target === wrap) { closeCard(); } };
        root.appendChild(wrap);
        closeX.focus();
      }
      function closeCard() {
        S.sel = null;
        var wrap = root.querySelector('.wy2-card-wrap');
        if (wrap) { wrap.parentNode.removeChild(wrap); }
        /* 回到原位置：滚动与缩放都没动过，确认一下就好 */
        var vp = root.querySelector('.wy2-viewport');
        if (vp) { vp.scrollLeft = S.scroll.left; vp.scrollTop = S.scroll.top; }
      }

      /* ---- 先落一次缩放；视口尺寸此时未必可靠，下一帧再按真实尺寸重算 ---- */
      applyZoom();
      requestAnimationFrame(function () {
        var vp = root.querySelector('.wy2-viewport');
        if (!vp) { return; }
        viewport = vp;
        applyZoom();
      });

      /* 键盘可达：Tab 到热点时给个明显轮廓（热点在 svg 里，用按钮代理太绕，
         这里给整张图一个可聚焦的入口，回车打开最近未学的字） */
      window.__wyDbg = window.__wyDbg || { taps: [] };
      window.__wyDbg.pickAt = pickAt;
      window.__wyDbg.state = function () {
        return { view: S.view, zoom: S.zoom, lens: S.lens ? S.lens.char : null,
                 sel: S.sel, zone: S.zone ? S.zone.id : null,
                 showHot: S.showHot, flow: S.flow ? S.flow.obj.char : null };
      };
      var focusBtn = App.el('button', 'wy2-focus-helper',
        '键盘：认下一个还没学的字');
      focusBtn.type = 'button';
      focusBtn.onclick = function () {
        var next = null;
        objs.some(function (it) { if (!it.done) { next = it; return true; } return false; });
        if (!next) { next = objs[0]; }
        S.lens = { char: next.o.char, x: next.o.x, y: next.o.y };
        setZoom(ZOOM_HINT[next.o.char] || 2.6, { x: next.o.x, y: next.o.y });
        setTimeout(function () { openCard(next); }, 60);
      };
      el.appendChild(focusBtn);

      if (s.clear) {
        var done = App.el('aside', 'wy2-zone-clear');
        done.appendChild(App.el('span', 'wy2-clear-seal', '已点亮'));
        done.appendChild(App.el('span', null,
          '「' + z.name + '」' + s.total + ' 个字都认过了，大地图上这一片亮了。'));
        var nxt = App.el('button', 'btn sm', '回大地图看点亮 →');
        nxt.type = 'button';
        nxt.onclick = backToWorld;
        done.appendChild(nxt);
        el.appendChild(done);
      }

      if (S.flow) { renderFlow(el, S.flow); }
    }

    function kindOf(ch) {
      var BODY = '人大女子目耳口止又足力';
      var NATURE = '日月雨火山丘谷石土泉川水田木林竹禾米屮豕鹿牛羊犬虎虫鱼隹';
      if (BODY.indexOf(ch) >= 0) { return '人体'; }
      if (NATURE.indexOf(ch) >= 0) { return '自然'; }
      return '器物';
    }

    /* ----------------------------------------------------------
       ③ 把笔画拼回去（本关的记录「学过了」由这一步落下）
       沿用原来的拖拽判定，只是把它收进学习卡之后。
       ---------------------------------------------------------- */
    function startFlow(it) {
      S.flow = {
        obj: it.o, zone: S.zone,
        placed: [], pool: shuffle(rangeOf(App.glyphStrokeCount(it.o.char))),
        verdict: '把下面的笔画拖进上面的格子里，摆回原来的位置。'
      };
      redrawZone();
      var el = root.querySelector('.wy2-flow');
      if (el) { el.scrollIntoView({ block: 'nearest' }); }
    }

    function renderFlow(host, flow) {
      var ch = flow.obj.char;
      var strokes = App.glyphStrokes(ch);
      var n = strokes.length;
      var box = App.el('section', 'wy2-flow');

      var head = App.el('div', 'wy2-flow-head');
      head.appendChild(App.el('b', null, '拼一拼「' + ch + '」'));
      head.appendChild(App.el('span', 'wy2-flow-count', n + ' 笔'));
      var x = App.el('button', 'btn sm', '收起');
      x.type = 'button';
      x.onclick = function () { S.flow = null; redrawZone(); };
      head.appendChild(x);
      box.appendChild(head);

      var wrap = App.el('div', 'wy2-flow-body');
      var ref = App.el('div', 'wy2-flow-ref');
      var rg = svgEl('svg');
      rg.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      rg.setAttribute('class', 'wy2-flow-refglyph');
      if (App.hasGlyph(ch)) { rg.innerHTML = App.glyphSvg(ch, 'currentColor'); }
      ref.appendChild(rg);
      ref.appendChild(App.el('span', null, '甲骨文原字'));
      wrap.appendChild(ref);

      var stageWrap = App.el('div', 'wy2-flow-stagewrap');
      var stage = svgEl('svg');
      stage.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      stage.setAttribute('class', 'wy2-flow-stage');
      var guide = svgEl('g');
      guide.setAttribute('class', 'wy2-flow-guide');
      if (App.hasGlyph(ch)) { guide.innerHTML = App.glyphSvg(ch, 'currentColor'); }
      stage.appendChild(guide);
      var placedG = svgEl('g');
      placedG.setAttribute('class', 'wy2-flow-placed');
      stage.appendChild(placedG);
      stageWrap.appendChild(stage);
      wrap.appendChild(stageWrap);
      box.appendChild(wrap);

      var tray = App.el('div', 'wy2-flow-tray');
      tray.appendChild(App.el('span', 'wy2-flow-tray-label', '笔画'));
      var pool = App.el('div', 'wy2-flow-pool');
      tray.appendChild(pool);
      box.appendChild(tray);

      var verdict = App.el('p', 'wy2-flow-verdict', flow.verdict);
      box.appendChild(verdict);
      host.appendChild(box);

      function paintPlaced() {
        App.clearNode(placedG);
        flow.placed.forEach(function (i) {
          var g = svgEl('g');
          g.setAttribute('class', 'wy2-flow-stroke');
          g.innerHTML = App.glyphStrokeSvg(ch, i, 'currentColor');
          placedG.appendChild(g);
        });
      }
      function paintPool() {
        App.clearNode(pool);
        flow.pool.forEach(function (i) {
          if (flow.placed.indexOf(i) >= 0) { return; }
          var c = strokes[i].c;
          var w = Math.max(c[2] - c[0], 1e-3);
          var h = Math.max(c[3] - c[1], 1e-3);
          var pad = Math.max(w, h) * 0.35 + 2;
          var b = App.el('div', 'wy2-piece');
          b.setAttribute('data-i', String(i));
          /* 把这一笔的画布包围盒写上：自动化测试靠它算出"该放哪儿"，
             也方便人工排查某一块为什么摆不进去。 */
          b.setAttribute('data-c', c.join(','));
          var sg = svgEl('svg');
          sg.setAttribute('viewBox', (c[0] - pad) + ' ' + (c[1] - pad) + ' ' +
            (w + pad * 2) + ' ' + (h + pad * 2));
          sg.setAttribute('class', 'wy2-piece-svg');
          sg.innerHTML = App.glyphStrokeSvg(ch, i, 'currentColor');
          b.appendChild(sg);
          attachDrag(b, i, c);
          pool.appendChild(b);
        });
        if (!pool.children.length) {
          pool.appendChild(App.el('span', 'wy2-flow-empty', '都摆上去了'));
        }
      }
      function attachDrag(node, idx, c) {
        var tx = (c[0] + c[2]) / 2, ty = (c[1] + c[3]) / 2;
        var tol = Math.max(16, Math.max(c[2] - c[0], c[3] - c[1]) * 0.55);
        node.setAttribute('data-target', tx + ',' + ty);
        node.setAttribute('data-tol', String(tol));
        node.addEventListener('pointerdown', function (ev) {
          ev.preventDefault();
          node.classList.add('dragging');
          try { node.setPointerCapture(ev.pointerId); } catch (e) { /* 忽略 */ }
          function move(e) {
            node.style.transform = 'translate(' + (e.clientX - ev.clientX) + 'px,' +
              (e.clientY - ev.clientY) + 'px)';
          }
          function up(e) {
            node.removeEventListener('pointermove', move);
            node.removeEventListener('pointerup', up);
            node.removeEventListener('pointercancel', up);
            node.classList.remove('dragging');
            node.style.transform = '';
            var r = stage.getBoundingClientRect();
            var px = (e.clientX - r.left) / r.width * CV;
            var py = (e.clientY - r.top) / r.height * CV;
            var d = Math.sqrt(Math.pow(px - tx, 2) + Math.pow(py - ty, 2));
            if (d <= tol) {
              flow.placed.push(idx);
              paintPlaced(); paintPool(); check();
            } else {
              var dx = tx - px, dy = ty - py;
              var hz = dx > 8 ? '右' : (dx < -8 ? '左' : '');
              var vt = dy > 8 ? '下' : (dy < -8 ? '上' : '');
              verdict.className = 'wy2-flow-verdict no';
              verdict.textContent = '✘ 没到位——这一笔该往「' + ((vt + hz) || '原处附近') +
                '」挪。已摆 ' + flow.placed.length + ' / ' + n + ' 笔。';
            }
          }
          node.addEventListener('pointermove', move);
          node.addEventListener('pointerup', up);
          node.addEventListener('pointercancel', up);
        });
      }
      function check() {
        if (flow.placed.length < n) {
          verdict.className = 'wy2-flow-verdict';
          verdict.textContent = '已摆 ' + flow.placed.length + ' / ' + n + ' 笔';
          return;
        }
        var p = markDone(flow.zone.id, ch);
        var s = zoneStat(p, flow.zone);
        verdict.className = 'wy2-flow-verdict ok';
        verdict.textContent = '✔ 拼成了「' + ch + '」，已记进「' + flow.zone.name + '」。'
          + (s.clear ? '这一片学完了，大地图上已经点亮。'
                     : '这一片还差 ' + (s.total - s.done) + ' 个字。');
        /* 记录落下后，重画小地图（印记与进度条跟着变） */
        setTimeout(function () { S.flow = null; redrawZone(); }, 1400);
      }

      paintPlaced(); paintPool();
      if (!n) {
        verdict.className = 'wy2-flow-verdict no';
        verdict.textContent = '这个字没有可拆的笔画。';
      }
    }

    render();
  }

  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function rangeOf(n) { var a = []; for (var i = 0; i < n; i++) { a.push(i); } return a; }
  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function unmount() {
    S.view = 'map'; S.zone = null; S.sel = null; S.lens = null;
    S.showHot = false; S.zoom = 1; S.flow = null; S.drag = null;
    S.scroll = { left: 0, top: 0 };
  }

  App.modes.register({
    id: 'wangyi-map',
    name: '殷商王邑',
    tagline: '在大地图上挑一片，点实物认甲骨文',
    desc: '五片主题区域任意顺序进入：在分区插画上点实物认甲骨文，认得的字就记下来。一片学完，大地图上对应的那一片便亮起，最终点亮整座王邑。',
    icon: '邑',
    accent: 'var(--bronze)',
    tags: ['五片任意进入', '61 个学习点', '点亮大地图'],
    layout: 'wide',
    minPlayers: 1, maxPlayers: 1,
    status: 'ready',
    data: { packs: [], assets: [] },
    mount: mount,
    unmount: unmount
  });

})(window.App = window.App || {});
