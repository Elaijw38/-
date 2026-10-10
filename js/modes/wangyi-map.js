/* ============================================================
   字趣 · 玩法模块：殷商王邑（关卡地图）
   —— 单张大拼图地图，分区块；解锁后点亮拼图块（静态高亮）。
      每个区块挂一种玩法，复用平台既有的拖拽/判定/存储，不重写核心逻辑。

   区块机制（机制名写在 levels.json 的 mechanic 字段）：
     boss     拆字：给甲骨字形，从四选一里认出它是什么构件
     pair     配对：甲骨形 ←→ 今字，左右两列点选配对
     oracle   卜辞拼字（素材待补，先占位）
     practice 原有单字选构练习（跳转到既有玩法）
   ============================================================ */
(function (App) {
  'use strict';

  var MAP = (App.levels && App.levels.map) || null;
  var STORE_KEY = 'wangyi';

  /* ---------- 进度存储 ----------
     { cleared: { zoneId: [已通关的 levelId, ...] } }
     复用平台统一的 ziqu. 前缀存储，与其它设置同处一处。 */
  function progress() {
    var p = App.store.get(STORE_KEY, null);
    if (!p || typeof p !== 'object') p = {};
    if (!p.cleared) p.cleared = {};
    return p;
  }
  function saveProgress(p) { App.store.set(STORE_KEY, p); }
  function zoneCleared(p, zoneId) {
    return (p.cleared[zoneId] || []).length;
  }
  function isLevelCleared(p, zoneId, levelId) {
    return (p.cleared[zoneId] || []).indexOf(levelId) >= 0;
  }
  function markCleared(zoneId, levelId) {
    var p = progress();
    if (!p.cleared[zoneId]) p.cleared[zoneId] = [];
    if (p.cleared[zoneId].indexOf(levelId) < 0) p.cleared[zoneId].push(levelId);
    saveProgress(p);
    return p;
  }

  /* 解锁规则：显式声明 unlocked:true 才默认开放；
     comingSoon（如卜辞素材未到位）一律不开放，即便写了 unlocked。
     既不声明 unlocked 也没有 unlock 条件的，视为未开放——
     闯关地图应当逐块收复，不能一上来全亮。 */
  function isZoneUnlocked(zone, p) {
    if (zone.comingSoon) return false;
    if (zone.unlock) {
      return zoneCleared(p, zone.unlock.after) >= (zone.unlock.need || 1);
    }
    return !!zone.unlocked;
  }
  function unlockText(zone) {
    if (zone.comingSoon) return '素材待补';
    var u = zone.unlock;
    if (!u) return '';
    var z = zoneById(u.after);
    return '通关「' + (z ? z.name : u.after) + '」' + (u.need || 1) + ' 关后解锁';
  }
  function zoneById(id) {
    if (!MAP) return null;
    return MAP.zones.filter(function (z) { return z.id === id; })[0] || null;
  }

  /* ---------- 小组件 ---------- */
  function glyphBox(name, cls, color) {
    var wrap = App.el('div', 'wy-glyph' + (cls ? ' ' + cls : ''));
    var svg = App.glyphSvg(name, color);
    if (svg) {
      wrap.innerHTML = '<svg viewBox="0 0 ' + (App.glyphs.canvas || 100) + ' ' +
        (App.glyphs.canvas || 100) + '">' + svg + '</svg>';
    } else {
      wrap.appendChild(App.el('span', 'wy-glyph-none', name));
    }
    return wrap;
  }

  /* ---------- 模式定义 ---------- */
  App.modes.register({
    id: 'wangyi-map',
    name: '殷商王邑',
    tagline: '在地图上闯关识字',
    desc: '一张王邑地图，三处地界各藏契文。点亮拼图块，逐块收复。',
    icon: '邑',
    accent: 'var(--bronze)',
    tags: ['闯关', '地图', '拆字', '配对'],
    minPlayers: 1, maxPlayers: 1,
    status: 'ready',
    data: { packs: [], assets: ['glyphs'] },
    mount: mount,
    unmount: function () { stopTimer(); }
  });

  /* ---------- 状态 ---------- */
  var S = {
    view: 'map',      /* map | zone | level */
    zone: null,
    level: null,
    picked: [],       /* 配对：已选中的左列下标 */
    matched: {},      /* 配对：已配成的左列下标 */
    timed: null
  };

  function stopTimer() {
    if (S.timed) { clearInterval(S.timed); S.timed = null; }
  }

  /* ============================================================
     挂载
     ============================================================ */
  function mount(host, ctx) {
    /* 每次挂载都从地图重新开始。
       S 是模块级状态，若不在挂载时重置，离开再进入会停留在
       上一次的区块/关卡视图（宿主里没有地图，看着像"什么都没加载"）。 */
    S.view = 'map';
    S.zone = null;
    S.level = null;
    S.picked = [];
    S.matched = {};
    stopTimer();

    var root = App.el('div', 'scene wangyi');
    host.appendChild(root);

    if (!MAP || !MAP.zones || !MAP.zones.length) {
      root.appendChild(App.el('p', 'lead', '关卡数据缺失（js/core/levels.json）。'));
      return;
    }

    function render() {
      App.clearNode(root);
      stopTimer();
      if (S.view === 'zone' && S.zone) renderZone(root);
      else if (S.view === 'level' && S.zone) renderLevel(root);
      else renderMap(root);
    }

    /* ---------- 地图 ---------- */
    function renderMap(el) {
      var p = progress();

      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', MAP.name));
      head.appendChild(App.el('span', 'wy-sub', MAP.subtitle || ''));
      el.appendChild(head);
      el.appendChild(App.el('p', 'lead', MAP.intro || ''));

      /* 单张大拼图：区块是 levels.json 里的多边形，咬合成一张地图。
         用内联 SVG 而非图片——无需生成素材、任意缩放不糊、
         描边与填充都能随主题变色（与平台既有做法一致）。 */
      var SVGNS = 'http://www.w3.org/2000/svg';
      var svg = document.createElementNS(SVGNS, 'svg');
      svg.setAttribute('class', 'wy-svg');
      svg.setAttribute('viewBox', MAP.viewBox || '0 0 1000 720');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', MAP.name + ' 地图');

      /* 先画所有区块，再把中央占卜坑压在最上层（它是叠在拼缝上的菱形） */
      var ordered = MAP.zones.slice().sort(function (a, b) {
        return (a.id === 'center' ? 1 : 0) - (b.id === 'center' ? 1 : 0);
      });

      ordered.forEach(function (z) {
        if (!z.poly) { return; }
        var unlocked = isZoneUnlocked(z, p);
        var done = zoneCleared(p, z.id);
        var total = (z.levels || []).length;
        var accent = z.color || 'var(--bronze-tint)';

        var g = document.createElementNS(SVGNS, 'g');
        g.setAttribute('class', 'wy-zone' + (unlocked ? ' on' : ' off') +
          (z.comingSoon ? ' soon' : ''));
        g.setAttribute('tabindex', '0');
        if (z.color) { g.style.setProperty('--wy-accent', accent); }

        var poly = document.createElementNS(SVGNS, 'polygon');
        poly.setAttribute('points', z.poly);
        poly.setAttribute('class', 'wy-zone-poly');
        g.appendChild(poly);

        var lab = z.label || [500, 360];
        var t = document.createElementNS(SVGNS, 'text');
        t.setAttribute('x', lab[0]);
        t.setAttribute('y', lab[1]);
        t.setAttribute('class', 'wy-z-name');
        t.setAttribute('text-anchor', 'middle');
        t.textContent = z.name;
        g.appendChild(t);

        var sub = document.createElementNS(SVGNS, 'text');
        sub.setAttribute('x', lab[0]);
        sub.setAttribute('y', lab[1] + 26);
        sub.setAttribute('class', 'wy-z-sub');
        sub.setAttribute('text-anchor', 'middle');
        var state;
        if (z.comingSoon) { state = '筹备中'; }
        else if (!unlocked) { state = '未解锁'; }
        else if (total && done >= total) { state = '已通 ' + done + '/' + total; }
        else if (total) { state = done + ' / ' + total; }
        else { state = '原有玩法'; }
        sub.textContent = z.rank + ' · ' + state;
        g.appendChild(sub);

        /* 已解锁的区块给一条朱砂括号线，做出"点亮"的静态高亮 */
        if (unlocked) {
          var ring = document.createElementNS(SVGNS, 'polygon');
          ring.setAttribute('points', z.poly);
          ring.setAttribute('class', 'wy-zone-ring');
          g.appendChild(ring);
        }
        /* 已全部通关：在角落盖一枚甲骨字形做印记 */
        if (total && done >= total && App.glyphSvg('卜')) {
          var mark = document.createElementNS(SVGNS, 'g');
          mark.setAttribute('class', 'wy-zone-mark');
          var s = 0.5, cx = lab[0] - 4, cy = lab[1] + 60;
          mark.setAttribute('transform',
            'translate(' + cx + ',' + cy + ') scale(' + s + ') translate(-50,-50)');
          mark.innerHTML = App.glyphSvg('卜', 'currentColor');
          g.appendChild(mark);
        }

        g.onclick = function () {
          var pp = progress();
          if (z.comingSoon) { App.toast('「' + z.name + '」的卜辞素材待补，先去看看别处。'); return; }
          if (!isZoneUnlocked(z, pp)) { App.toast('尚未解锁：' + unlockText(z)); return; }
          S.view = 'zone'; S.zone = z; render();
        };
        g.onkeydown = function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); g.onclick(); }
        };
        if (!unlocked) { g.setAttribute('aria-disabled', 'true'); }
        svg.appendChild(g);
      });

      var mapWrap = App.el('div', 'wy-map');
      mapWrap.appendChild(svg);
      el.appendChild(mapWrap);

      /* 图例：说明点亮/锁定/筹备中的差别，避免玩家猜 */
      var legend = App.el('div', 'wy-legend');
      [['点亮·可入', 'on'], ['未解锁', 'off'], ['筹备中', 'soon']].forEach(function (it) {
        var sp = App.el('span', 'wy-lg wy-lg-' + it[1]);
        sp.appendChild(App.el('i', 'wy-lg-dot'));
        sp.appendChild(document.createTextNode(it[0]));
        legend.appendChild(sp);
      });
      el.appendChild(legend);

      /* 侧边入口：原有练习 + 进度重置 */
      var side = App.el('div', 'wy-side');
      var sp = App.el('button', 'btn', '单字选构练习（原有玩法）');
      sp.onclick = function () { ctx.nav.modes(); };
      side.appendChild(sp);
      var reset = App.el('button', 'btn sm', '重置闯关进度');
      reset.onclick = function () {
        if (!window.confirm('重置后所有已点亮的区块会重新锁上，确定吗？')) return;
        App.store.del(STORE_KEY);
        App.toast('闯关进度已重置');
        render();
      };
      side.appendChild(reset);
      el.appendChild(side);
    }

    /* ---------- 区块：关卡列表 ---------- */
    function renderZone(el) {
      var z = S.zone, p = progress();
      var back = App.el('button', 'btn sm', '← 回到地图');
      back.onclick = function () { S.view = 'map'; S.zone = null; render(); };
      el.appendChild(back);

      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', z.name));
      head.appendChild(App.el('span', 'wy-cell-rank', z.rank));
      el.appendChild(head);
      el.appendChild(App.el('p', 'lead', (z.desc || '') + '　' + (z.hint || '')));

      if (z.comingSoon || !(z.levels || []).length) {
        var box = App.el('div', 'sect');
        box.appendChild(App.el('div', 'hint',
          '本区块的玩法是「' + (z.hint || z.mechanic) + '」，但**卜辞文本素材尚未取得**，' +
          '为避免编造卜辞，内容暂缺。地图分区与解锁规则已就绪，素材到位后填入 levels 即可开玩。'));
        el.appendChild(box);
        return;
      }

      var list = App.el('div', 'wy-levels');
      z.levels.forEach(function (lv, i) {
        var cleared = isLevelCleared(p, z.id, lv.id);
        var prevDone = i === 0 || isLevelCleared(p, z.id, z.levels[i - 1].id);
        var open = cleared || prevDone;
        var card = App.el('div', 'wy-level' + (cleared ? ' done' : '') + (open ? '' : ' locked'));
        var no = App.el('span', 'wy-level-no', String(i + 1));
        card.appendChild(no);
        var t = App.el('div', 'wy-level-t');
        t.appendChild(App.el('div', 'wy-level-name',
          lv.char ? ('认出「' + lv.char + '」') : ('第 ' + (i + 1) + ' 组')));
        if (lv.hint) t.appendChild(App.el('div', 'wy-level-hint', lv.hint));
        card.appendChild(t);
        if (cleared) card.appendChild(App.el('span', 'wy-done', '已过'));
        else if (!open) card.appendChild(App.el('span', 'wy-lock', '先过上一关'));
        card.onclick = function () {
          if (!open) { App.toast('先通过上一关'); return; }
          S.view = 'level'; S.level = { zone: z, index: i, data: lv }; S.picked = []; S.matched = {};
          render();
        };
        list.appendChild(card);
      });
      el.appendChild(list);
    }

    /* ---------- 关卡：按机制分发 ---------- */
    function renderLevel(el) {
      var z = S.level.zone, lv = S.level.data;
      var back = App.el('button', 'btn sm', '← 回到「' + z.name + '」');
      back.onclick = function () { S.view = 'zone'; S.level = null; render(); };
      el.appendChild(back);

      var mech = z.mechanic;
      if (mech === 'boss') renderBoss(el, z, lv);
      else if (mech === 'pair') renderPair(el, z, lv);
      else if (mech === 'divine') renderDivine(el, z, lv);
      else renderPlaceholder(el, z, lv);
    }

    /* 通关：加分、存进度、可能解锁新区块 */
    function pass(zone, levelId, msg) {
      var before = progress();
      var wasLocked = MAP.zones.filter(function (z) { return !isZoneUnlocked(z, before); })
        .map(function (z) { return z.id; });
      var p = markCleared(zone.id, levelId);
      var nowUnlocked = MAP.zones.filter(function (z) {
        return wasLocked.indexOf(z.id) >= 0 && isZoneUnlocked(z, p);
      });
      if (nowUnlocked.length) {
        App.toast('新的地界显现：' + nowUnlocked.map(function (z) { return z.name; }).join('、'), 3600);
      } else if (msg) {
        App.toast(msg);
      }
    }

    /* ---------- 机制一：拆字（BOSS） ---------- */
    function renderBoss(el, z, lv) {
      var idx = S.level.index;
      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', '第 ' + (idx + 1) + ' 关 · ' + z.name));
      el.appendChild(head);

      var stage = App.el('div', 'wy-stage');
      var q = App.el('div', 'wy-question');
      q.appendChild(App.el('div', 'wy-q-label', '这个甲骨字形是哪一个构件？'));
      q.appendChild(glyphBox(lv.char, 'lg'));
      stage.appendChild(q);
      el.appendChild(stage);

      /* 干扰项取自整个字库（同域干扰更有难度，但字库本身已是甲骨常用字）。
         不用 levels.json 的分区索引——那个索引会与实际关卡内容脱节；
         统一字库 + 排除正解，才能保证任何关卡都凑得齐选项。 */
      var pool = Object.keys(App.glyphs.parts || {}).filter(function (n) {
        return n !== lv.char;
      });
      pool = App.shuffle ? App.shuffle(pool) : pool;
      var opts = [lv.char].concat(pool.slice(0, 3));
      opts = App.shuffle ? App.shuffle(opts) : opts;

      var row = App.el('div', 'wy-opts');
      var answered = false;
      opts.forEach(function (name) {
        var b = App.el('div', 'wy-opt');
        b.appendChild(App.el('span', 'wy-opt-name', name));
        var g = App.glyphSvg(name, 'currentColor');
        if (g) {
          /* 用块级容器承载 SVG：行内 span 里的 svg 不会按预期占位 */
          var form = App.el('span', 'wy-opt-form');
          form.innerHTML = '<svg viewBox="0 0 ' + (App.glyphs.canvas || 100) + ' ' +
            (App.glyphs.canvas || 100) + '">' + g + '</svg>';
          b.appendChild(form);
        }
        b.onclick = function () {
          if (answered) return;
          answered = true;
          var ok = name === lv.char;
          b.className += ok ? ' ok' : ' no';
          if (!ok) {
            /* 标出正确项 */
            Array.prototype.forEach.call(row.children, function (c) {
              if (c.querySelector('.wy-opt-name').textContent === lv.char) c.className += ' ok';
            });
          }
          var v = App.el('div', 'verdict ' + (ok ? 'ok' : 'no'));
          v.textContent = ok
            ? '✔ 正是「' + lv.char + '」' + (lv.hint ? '　—　' + lv.hint : '')
            : '✘ 这是「' + name + '」，正确答案是「' + lv.char + '」';
          el.appendChild(v);
          var bar = App.el('div', 'bar');
          if (ok) pass(z, lv.id, '已通关');
          var hasNext = ok && (S.level.index + 1) < (z.levels || []).length;
          var next = App.el('button', 'btn primary',
            hasNext ? '下一关' : (ok ? '回到区块' : '回到关卡列表'));
          next.onclick = function () {
            if (hasNext) {
              S.level = { zone: z, index: S.level.index + 1, data: z.levels[S.level.index + 1] };
            } else { S.view = 'zone'; S.level = null; }
            render();
          };
          bar.appendChild(next);
          if (!ok) {
            var again = App.el('button', 'btn', '再试一次');
            again.onclick = function () { S.picked = []; render(); };
            bar.appendChild(again);
          }
          el.appendChild(bar);
        };
        row.appendChild(b);
      });
      el.appendChild(row);
    }

    /* ---------- 机制三：卜辞拼字（读卜辞，选出所需构件） ----------
       数据来自 levels.json，其内容源自项目内既有素材 data.js 的 DIVINE 数组
       （5 条卜问，每条自带所问、所需构件与吉凶结果），未编造卜辞。 */
    function renderDivine(el, z, lv) {
      var idx = S.level.index;
      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', '第 ' + (idx + 1) + ' 关 · ' + z.name));
      head.appendChild(App.el('span', 'wy-cell-rank', lv.divine || ''));
      el.appendChild(head);

      /* 卜辞问句：做成一块"卜骨"卡片，与地图中央的菱形呼应 */
      var ask = App.el('div', 'wy-ask');
      ask.appendChild(App.el('div', 'wy-ask-label', '卜辞'));
      ask.appendChild(App.el('div', 'wy-ask-text', lv.q || ''));
      if (lv.note) ask.appendChild(App.el('div', 'wy-ask-note', '※ ' + lv.note));
      el.appendChild(ask);

      el.appendChild(App.el('div', 'wy-q-label',
        '这条卜辞问的是什么事？选出它所需的 ' + (lv.parts || []).length + ' 个构件'));

      /* 候选来自整个字库，含正解与干扰 */
      var need = (lv.parts || []).slice();
      var pool = Object.keys(App.glyphs.parts || {}).filter(function (n) {
        return need.indexOf(n) < 0;
      });
      pool = App.shuffle ? App.shuffle(pool) : pool;
      var distract = Math.max(4, 8 - need.length);
      var opts = need.concat(pool.slice(0, distract));
      opts = App.shuffle ? App.shuffle(opts) : opts;

      var chosen = [];
      var row = App.el('div', 'wy-opts');
      var answered = false;
      var bar = App.el('div', 'bar');
      var confirmBtn = null;

      function repaint() {
        Array.prototype.forEach.call(row.children, function (c) {
          var nm = c.getAttribute('data-nm');
          var on = chosen.indexOf(nm) >= 0;
          c.className = 'wy-opt' + (on ? ' on' : '');
        });
        if (confirmBtn) {
          confirmBtn.textContent = chosen.length
            ? ('契刻（已选 ' + chosen.length + '/' + need.length + '）')
            : '契刻';
          confirmBtn.disabled = chosen.length === 0;
          /* 暴露状态给自查脚本，避免驱动靠时序猜测（曾因此误判） */
          confirmBtn.setAttribute('data-chosen', chosen.join(''));
          confirmBtn.setAttribute('data-answered', answered ? '1' : '0');
        }
      }

      opts.forEach(function (name) {
        var b = App.el('div', 'wy-opt');
        b.setAttribute('data-nm', name);
        b.appendChild(App.el('span', 'wy-opt-name', name));
        var g = App.glyphSvg(name, 'currentColor');
        if (g) {
          var form = App.el('span', 'wy-opt-form');
          form.innerHTML = '<svg viewBox="0 0 ' + (App.glyphs.canvas || 100) + ' ' +
            (App.glyphs.canvas || 100) + '">' + g + '</svg>';
          b.appendChild(form);
        }
        b.onclick = function () {
          if (answered) { return; }
          var i = chosen.indexOf(name);
          if (i >= 0) { chosen.splice(i, 1); } else { chosen.push(name); }
          repaint();
        };
        row.appendChild(b);
      });
      el.appendChild(row);

      confirmBtn = App.el('button', 'btn primary', '契刻');
      confirmBtn.disabled = true;
      confirmBtn.onclick = function () {
        if (answered) { return; }
        answered = true;
        /* 顺序不计：构件是集合 */
        var sortedNeed = need.slice().sort().join('');
        var sortedGot = chosen.slice().sort().join('');
        var ok = sortedNeed === sortedGot;
        var missing = need.filter(function (n) { return chosen.indexOf(n) < 0; });
        var extra = chosen.filter(function (n) { return need.indexOf(n) < 0; });
        repaint();   /* 让 data-answered 等状态同步给自查脚本 */

        Array.prototype.forEach.call(row.children, function (c) {
          var nm = c.getAttribute('data-nm');
          var should = need.indexOf(nm) >= 0;
          var has = chosen.indexOf(nm) >= 0;
          if (should) { c.className = 'wy-opt ok'; }
          else if (has) { c.className = 'wy-opt no'; }
          else { c.className = 'wy-opt'; }
        });

        var v = App.el('div', 'verdict ' + (ok ? 'ok' : 'no'));
        v.textContent = ok
          ? ('✔ 正是此事的构件：' + need.join('＋') + '　—　' + (lv.ok || ''))
          : '✘ ' + (missing.length ? ('少了 ' + missing.join('、') + '；') : '') +
            (extra.length ? ('多了 ' + extra.join('、') + '；') : '') +
            '应为 ' + need.join('＋');
        el.appendChild(v);

        if (ok) { pass(z, lv.id, '已通关'); }
        var hasNext = ok && (S.level.index + 1) < (z.levels || []).length;
        var nx = App.el('button', 'btn primary',
          hasNext ? '下一关' : (ok ? '回到区块' : '回到关卡列表'));
        nx.onclick = function () {
          if (hasNext) {
            S.level = { zone: z, index: S.level.index + 1, data: z.levels[S.level.index + 1] };
          } else { S.view = 'zone'; S.level = null; }
          render();
        };
        bar.appendChild(nx);
        if (!ok) {
          var again = App.el('button', 'btn', '再试一次');
          again.onclick = function () { render(); };
          bar.appendChild(again);
        }
        el.appendChild(bar);
      };
      bar.appendChild(confirmBtn);
      el.appendChild(bar);
      repaint();
    }

    /* ---------- 机制二：配对（甲骨形 ←→ 今字） ---------- */
    function renderPair(el, z, lv) {
      var idx = S.level.index;
      var head = App.el('div', 'wy-head');
      head.appendChild(App.el('h3', 'wy-title', '第 ' + (idx + 1) + ' 关 · ' + z.name));
      el.appendChild(head);

      var names = (lv.pairs || []).slice();
      var left = names.slice();
      var right = App.shuffle ? App.shuffle(names.slice()) : names.slice();
      S.picked = []; S.matched = {};
      var total = left.length;
      var got = 0;

      var wrap = App.el('div', 'wy-pair');
      var colL = App.el('div', 'wy-pair-col');
      var colR = App.el('div', 'wy-pair-col');

      el.appendChild(App.el('div', 'wy-q-label', '左边是甲骨形，右边是今字，点选配对'));

      function repaint() {
        Array.prototype.forEach.call(colL.children, function (c, i) {
          c.className = 'wy-pcard' + (S.matched[i] ? ' done' : (S.picked.indexOf(i) >= 0 ? ' sel' : ''));
        });
      }

      left.forEach(function (name, i) {
        var c = App.el('div', 'wy-pcard');
        c.appendChild(glyphBox(name, 'sm'));
        c.onclick = function () {
          if (S.matched[i]) return;
          S.picked = (S.picked[0] === i) ? [] : [i];
          repaint();
        };
        colL.appendChild(c);
      });

      right.forEach(function (name) {
        var c = App.el('div', 'wy-pcard');
        c.appendChild(App.el('span', 'wy-pchar', name));
        c.onclick = function () {
          if (!S.picked.length) { App.toast('先在左边选一个甲骨形'); return; }
          var i = S.picked[0];
          if (left[i] !== name) {
            c.className = 'wy-pcard no';
            setTimeout(function () { c.className = 'wy-pcard'; }, 500);
            App.toast('不是这个');
            return;
          }
          S.matched[i] = true;
          S.picked = [];
          c.className = 'wy-pcard done';
          got++;
          repaint();
          if (got === total) {
            pass(z, lv.id, '全部配对成功');
            var v = App.el('div', 'verdict ok');
            v.textContent = '✔ 全部配对成功';
            el.appendChild(v);
            var bar = App.el('div', 'bar');
            var next = App.el('button', 'btn primary',
              (S.level.index + 1 < (z.levels || []).length) ? '下一关' : '回到区块');
            next.onclick = function () {
              if (S.level.index + 1 < z.levels.length) {
                S.level = { zone: z, index: S.level.index + 1, data: z.levels[S.level.index + 1] };
              } else { S.view = 'zone'; S.level = null; }
              render();
            };
            bar.appendChild(next);
            el.appendChild(bar);
          }
        };
        colR.appendChild(c);
      });

      wrap.appendChild(colL);
      wrap.appendChild(colR);
      el.appendChild(wrap);
    }

    function renderPlaceholder(el, z, lv) {
      var box = App.el('div', 'sect');
      box.appendChild(App.el('div', 'hint',
        '本关机制「' + z.mechanic + '」的内容素材尚未取得，暂不可玩。'));
      el.appendChild(box);
    }

    render();
    return root;
  }

})(window.App = window.App || {});
