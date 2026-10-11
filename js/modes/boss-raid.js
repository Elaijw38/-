/* ============================================================
   字趣 · 玩法模块：构件讨伐（BOSS 战）

   核心逻辑：拆字为武，组构为招，繁笔破防。

   界面（本版重做）
     · 选关：**线性关卡**。21 关排成一条路径，逐关推进，通关即解锁下一关。
     · 作战：**横版对战**。左侧预留「项目形象」位，右侧是 BOSS 形象，
       上有 HUD（关卡 / 阶段 / 血量），下有提示、战报与操作。
     · 战斗逻辑与上一版完全一致，只换了排布与外观。

   三档 BOSS（与关卡顺序一致：一阶 6 → 二阶 6 → 终极 9）
     一阶 合体字（涉 鸣 焚 逐 安 家）身体＝构件拼成，拆构件
     二阶 独体字（山 人 木 日 月 水）身上无构件，直接拆笔画
     终极 繁复字（象 龍 鳥 鼓 馬 龜 舞 車 虎）图画型古字，只能斩笔画

   战斗三阶段
     1 构件压制 → 2 构件崩坏（构件攻击失效）→ 3 笔画终局（斩断全部笔画即杀）

   数据在 js/core/levels.json 的 boss 段，代码不写死任何字表。
   ============================================================ */
(function (App) {
  'use strict';

  var BOSS = (App.levels && App.levels.boss) || null;
  var SVGNS = 'http://www.w3.org/2000/svg';
  var CV = 100;
  var STORE_KEY = 'bossraid';

  /* 构件 → 击破效果。对应设计稿：止封走位、口封印技能、水火消属性。 */
  var EFFECT = {
    '止': ['封走位', '止——它的腿。斩断之后，这尊东西再也挪不动一步。'],
    '口': ['封印技能', '口——它的喉咙。击碎之后，吼叫与呼召全部封住。'],
    '水': ['消水属性', '水——它的水脉。断开之后，水属性攻击当场失效。'],
    '火': ['消火属性', '火——它的火种。熄灭之后，火属性攻击当场失效。'],
    '宀': ['破甲', '宀——它的屋顶。掀掉之后，护甲露出一整片裂口。'],
    '木': ['断筋骨', '木——它的骨干。折了之后，整个形体开始塌。'],
    '隹': ['断羽翼', '隹——它的翅膀。扯下之后，再飞不起来。'],
    '豕': ['断冲撞', '豕——它的冲力。卸了之后，只剩原地打转。'],
    '女': ['乱心神', '女——它的依凭。散去之后，身形晃了一下。']
  };
  function effectOf(ch) {
    return EFFECT[ch] || ['削弱', ch + '——被拆了下来，形体缺了一块。'];
  }

  /* ---------- 小工具 ---------- */
  function svgEl(tag) { return document.createElementNS(SVGNS, tag); }
  function parts(name) { return (App.glyphs && App.glyphs.parts) ? App.glyphs.parts[name] : null; }

  /* 单笔的 path（可指定描边粗细，用来做更宽的点击热区） */
  function strokePath(ch, i, color, mul) {
    var g = parts(ch);
    if (!g || !g.pieces[i]) { return ''; }
    return '<g transform="' + g.transform + '"><path d="' + g.pieces[i].d +
      '" fill="none" stroke="' + color + '" stroke-width="' +
      (g.strokeWidth * (mul || 1)) + '" stroke-linecap="round" stroke-linejoin="round"/></g>';
  }

  /* 把 N 个构件并排拼成一个身体：每个缩到 1/N 宽 */
  function compLayout(i, n) {
    var s = 1 / n;
    return 'translate(' + (i * CV * s).toFixed(3) + ',0) scale(' + s.toFixed(5) + ')';
  }

  /* ---------- 关卡表：把三档拍平成一串线性关卡 ---------- */
  function levelList() {
    var out = [];
    (BOSS && BOSS.tiers ? BOSS.tiers : []).forEach(function (t) {
      (t.list || []).forEach(function (b) { out.push({ tier: t, data: b }); });
    });
    return out;
  }
  function levelCount() { return levelList().length; }

  /* ---------- 关卡进度（存在本机） ---------- */
  function prog() {
    var p = App.store.get(STORE_KEY, null);
    if (!p || typeof p !== 'object' || !Array.isArray(p.cleared)) { p = { cleared: [] }; }
    return p;
  }
  function saveProg(p) { App.store.set(STORE_KEY, p); }
  function isCleared(i) { return prog().cleared.indexOf(i) >= 0; }
  function unlocked(i) { return i <= 0 || isCleared(i - 1); }
  function markCleared(i) {
    var p = prog();
    if (p.cleared.indexOf(i) < 0) { p.cleared.push(i); saveProg(p); }
  }
  function clearedCount() { return prog().cleared.length; }

  var S = {
    view: 'track',      /* track（线性选关）| fight | win */
    idx: 0,             /* 当前关卡序号（0 基） */
    boss: null, tier: null,
    phase: 1, hp: 100, broken: [], cut: [], log: [], hint: false
  };

  /* ============================================================
     挂载
     ============================================================ */
  function mount(host, ctx) {
    hardReset();
    var root = App.el('div', 'scene boss-raid');
    host.appendChild(root);

    if (!BOSS || !BOSS.tiers || !BOSS.tiers.length) {
      root.appendChild(App.el('p', 'lead', 'BOSS 数据缺失（js/core/levels.json 的 boss 段）。'));
      return;
    }

    function render() {
      App.clearNode(root);
      if (S.view === 'fight' && S.boss) { renderFight(root); return; }
      if (S.view === 'win' && S.boss) { renderWin(root); return; }
      renderTrack(root);
    }

    function hardReset() {
      S.view = 'track'; S.idx = 0; S.boss = null; S.tier = null;
      S.phase = 1; S.hp = 100; S.broken = []; S.cut = []; S.log = []; S.hint = false;
    }

    function say(kind, title, text) {
      S.log.unshift({ kind: kind, title: title, text: text });
      S.log = S.log.slice(0, 6);
    }

    /* 进入某一关 */
    function enter(i) {
      var L = levelList();
      if (i < 0 || i >= L.length || !unlocked(i)) { return; }
      S.idx = i;
      S.boss = L[i].data;
      S.tier = L[i].tier;
      S.view = 'fight';
      S.phase = 1; S.hp = 100; S.broken = []; S.cut = []; S.log = []; S.hint = false;
      say('sys', '第 ' + (i + 1) + ' 关 · 讨伐开始',
        '一尊 ' + segOf(S.boss) + ' 段的古字挡在面前。拆开它，就知道是哪个字了。');
      render();
    }

    /* 第一个"未通关且已解锁"的关卡序号；全通则返回 -1 */
    function firstOpen() {
      var L = levelList();
      for (var i = 0; i < L.length; i++) {
        if (!isCleared(i) && unlocked(i)) { return i; }
      }
      return -1;
    }

    /* ============================================================
       一、线性关卡路径
       ============================================================ */
    function renderTrack(el) {
      var L = levelList();
      var p = prog();

      var head = App.el('div', 'bo-head');
      head.appendChild(App.el('h3', 'bo-title', '构件讨伐'));
      head.appendChild(App.el('span', 'bo-sub', '拆字为武 · 组构为招 · 繁笔破防'));
      el.appendChild(head);

      var bar = App.el('div', 'bo-progress');
      bar.appendChild(App.el('span', 'bo-progtext',
        '已通关 ' + p.cleared.length + ' / ' + L.length));
      var meter = App.el('span', 'bo-progmeter');
      var fill = App.el('i', 'bo-progfill');
      fill.style.width = (L.length ? Math.round(p.cleared.length / L.length * 100) : 0) + '%';
      meter.appendChild(fill);
      bar.appendChild(meter);
      el.appendChild(bar);

      el.appendChild(App.el('p', 'lead',
        '一条线走到底：拆得动构件的就拆构件；构件混同、拆不动的图画型古字，'
        + '只能进笔画终局。通关一关，解锁下一关。'));

      /* 路径：横向一条，节点之间用连接线串起来 */
      var track = App.el('div', 'bo-track');
      var next = firstOpen();
      L.forEach(function (lv, i) {
        if (i > 0) {
          track.appendChild(App.el('span', 'bo-link' + (isCleared(i - 1) ? ' done' : '')));
        }
        var open = unlocked(i);
        var done = isCleared(i);
        var b = lv.data;

        var node = App.el('button', 'bo-node bo-spoiler' + (done ? ' done' : '') +
          (open ? '' : ' locked') + (i === next ? ' next' : ''));
        node.setAttribute('aria-label', '第 ' + (i + 1) + ' 关 ' + b.char +
          (done ? '（已通关）' : (open ? '' : '（未解锁）')));

        node.appendChild(App.el('span', 'bo-node-num', String(i + 1)));

        /* 字形外面套一层定位壳，好让"答案"正好压在甲骨形上浮出——
           这样节点里不用为空出来的答案预留一整行。 */
        var gw = App.el('div', 'bo-nodeglyphwrap');
        var sv = svgEl('svg');
        sv.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
        sv.setAttribute('class', 'bo-nodeglyph');
        if (lv.tier.kind === 'compound' && b.comps && b.comps.length) {
          sv.innerHTML = (b.comps || []).map(function (c, k) {
            return '<g transform="' + compLayout(k, b.comps.length) + '">' +
              App.glyphSvg(c, 'currentColor') + '</g>';
          }).join('');
        } else if (App.hasGlyph(b.char)) {
          sv.innerHTML = App.glyphSvg(b.char, 'currentColor');
        }
        gw.appendChild(sv);

        /* 不把现代字直接印在甲骨形上：默认只见甲骨，
           鼠标悬停 / 键盘聚焦 / 按住（触屏）时才浅浅浮出，压在字形中央。
           已通关的关卡先前揭晓过，就常显。 */
        gw.appendChild(App.el('span',
          'bo-node-name bo-spoiler-a' + (done ? ' shown' : ''), b.char));
        node.appendChild(gw);
        node.appendChild(App.el('span', 'bo-node-meta',
          done ? '已通关'
               : (open ? ((b.comps && b.comps.length) ? '构件 ' + b.comps.length + ' 块'
                                                      : (b.seg || 0) + ' 笔')
                       : '未解锁')));
        if (open) {
          node.onclick = function () { enter(i); };
        } else {
          node.disabled = true;
        }
        track.appendChild(node);
      });
      el.appendChild(track);

      var side = App.el('div', 'wy-side');
      if (next >= 0 && p.cleared.length) {
        var cont = App.el('button', 'btn primary', '继续第 ' + (next + 1) + ' 关');
        cont.onclick = function () { enter(next); };
        side.appendChild(cont);
      } else if (next === 0) {
        var st = App.el('button', 'btn primary', '从第 1 关开始');
        st.onclick = function () { enter(0); };
        side.appendChild(st);
      }
      /* 21 关一条锁链，演示时一关关打通太慢，留个后门 */
      var all = App.el('button', 'btn sm ghost', '解锁全部（演示用）');
      all.onclick = function () {
        if (!window.confirm('把前 20 关都标记为已通关，直接解锁全部关卡？')) { return; }
        var q = prog();
        for (var i = 0; i < L.length - 1; i++) {
          if (q.cleared.indexOf(i) < 0) { q.cleared.push(i); }
        }
        saveProg(q);
        render();
      };
      side.appendChild(all);
      var back = App.el('button', 'btn sm', '回到玩法列表');
      back.onclick = function () { ctx.nav.modes(); };
      side.appendChild(back);
      el.appendChild(side);
    }

    /* ============================================================
       二、横版作战
       ============================================================ */
    function isCompound() {
      return !!(S.boss && S.tier && S.tier.kind === 'compound' && (S.boss.comps || []).length);
    }
    function pieceCount() {
      if (isCompound()) { return S.boss.comps.length; }
      return App.glyphStrokeCount(S.boss.char) || 1;
    }
    function strokeTotal() {
      if (isCompound()) {
        return (S.boss.comps || []).reduce(function (n, c) {
          return n + (App.glyphStrokeCount(c) || 0);
        }, 0);
      }
      return App.glyphStrokeCount(S.boss.char) || 1;
    }
    /* 段数（笔画数）。合体字在数据集里没有完整甲骨形，levels.json 里记的 seg 是 0，
       必须由各构件的段数相加得到——否则界面上会出现"一尊 ? 段的古字"。 */
    function segOf(b) {
      if (b && b.comps && b.comps.length) {
        return b.comps.reduce(function (n, c) {
          return n + (App.glyphStrokeCount(c) || 0);
        }, 0);
      }
      return (b && b.seg) || (App.glyphStrokeCount(b && b.char) || 0);
    }

    function compIndex(ci, j) {
      var n = 0;
      for (var i = 0; i < ci; i++) { n += App.glyphStrokeCount(S.boss.comps[i]); }
      return n + j;
    }
    function hitAll(c, mul) {
      var g = parts(c);
      if (!g || !g.pieces) { return ''; }
      return g.pieces.map(function (p, i) { return strokePath(c, i, 'rgba(0,0,0,0)', mul); }).join('');
    }

    /* 我方面板上的进度：用真实数据，不放没有机制支撑的假血条 */
    function myProgress() {
      if (S.phase === 3) { return { now: S.cut.length, all: strokeTotal(), label: '斩断进度' }; }
      return { now: S.broken.length, all: pieceCount(), label: '拆解进度' };
    }

    function renderFight(el) {
      var b = S.boss;

      /* —— 顶部 HUD —— */
      var hud = App.el('div', 'bd-hud');
      var hudL = App.el('div', 'bd-hud-left');
      var back = App.el('button', 'btn sm ghost', '← 关卡');
      back.onclick = function () { S.view = 'track'; S.boss = null; render(); };
      hudL.appendChild(back);
      hudL.appendChild(App.el('span', 'bd-lv',
        '第 ' + (S.idx + 1) + ' 关 / ' + levelCount()));
      hudL.appendChild(App.el('span', 'bd-tier', S.tier.name));
      hud.appendChild(hudL);

      var ph = App.el('div', 'bd-phases');
      ['构件压制', '构件崩坏', '笔画终局'].forEach(function (name, i) {
        var d = App.el('span', 'bd-phase' + (S.phase === i + 1 ? ' on' : '') +
          (S.phase > i + 1 ? ' done' : ''));
        d.appendChild(App.el('i', 'bd-phdot'));
        d.appendChild(App.el('b', null, name));
        ph.appendChild(d);
      });
      hud.appendChild(ph);
      el.appendChild(hud);

      /* —— 横版战场 —— */
      var field = App.el('div', 'bd-field' +
        (S.phase === 2 ? ' broken' : '') + (S.phase === 3 ? ' final' : ''));

      /* 左：项目形象预留位（后续换成本作形象立绘） */
      var hero = App.el('div', 'bd-hero');
      var mp = myProgress();
      var hh = App.el('div', 'bd-side-head');
      hh.appendChild(App.el('span', 'bd-side-name', '字趣'));
      hh.appendChild(App.el('span', 'bd-side-role', mp.label + ' ' + mp.now + ' / ' + mp.all));
      hero.appendChild(hh);
      var hbar = App.el('span', 'bd-sidebar');
      var hfill = App.el('i', 'bd-sidefill hero');
      hfill.style.width = Math.round(mp.now / Math.max(1, mp.all) * 100) + '%';
      hbar.appendChild(hfill);
      hero.appendChild(hbar);
      var slot = App.el('div', 'bd-hero-slot');
      slot.appendChild(App.el('span', 'bd-slot-tag', '项目形象'));
      slot.appendChild(App.el('span', 'bd-slot-note', '预留位 · 后续替换为角色立绘'));
      hero.appendChild(slot);
      field.appendChild(hero);

      /* 中：远景（纯装饰，不接收指针事件，不挡 BOSS 的点击） */
      var sky = App.el('div', 'bd-scene');
      sky.appendChild(App.el('span', 'bd-sun'));
      sky.appendChild(App.el('span', 'bd-cloud c1'));
      sky.appendChild(App.el('span', 'bd-cloud c2'));
      sky.appendChild(App.el('span', 'bd-hill h1'));
      sky.appendChild(App.el('span', 'bd-hill h2'));
      field.appendChild(sky);

      /* 右：BOSS 形象 */
      var bossSide = App.el('div', 'bd-boss bo-spoiler');
      var bh = App.el('div', 'bd-side-head');
      /* BOSS 名同样不直说：先给一个「?」，指针落到 BOSS 一侧才浅浅浮出。
         副标题换成中性的笔画数——写 b.note 里那句（"水与止缺一不可"）等于报构件。 */
      var nm = App.el('span', 'bd-side-name');
      nm.appendChild(App.el('i', 'bd-ask', '？'));
      nm.appendChild(App.el('i', 'bo-spoiler-a', b.char));
      bh.appendChild(nm);
      bh.appendChild(App.el('span', 'bd-side-role', segOf(b) + ' 段笔画'));
      bossSide.appendChild(bh);
      var bbar = App.el('span', 'bd-sidebar');
      var bfill = App.el('i', 'bd-sidefill boss');
      bfill.style.width = Math.max(0, S.hp) + '%';
      bbar.appendChild(bfill);
      bossSide.appendChild(bbar);
      bossSide.appendChild(App.el('span', 'bd-hpnum',
        '形体完整度 ' + Math.max(0, Math.round(S.hp)) + '%'));

      var bodyBox = App.el('div', 'bd-bodybox');
      var sv = svgEl('svg');
      sv.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      sv.setAttribute('class', 'bd-body');
      sv.innerHTML = bodyMarkup();
      bodyBox.appendChild(sv);
      bossSide.appendChild(bodyBox);
      field.appendChild(bossSide);

      field.appendChild(App.el('span', 'bd-ground'));
      el.appendChild(field);

      /* —— 提示 —— */
      var tip = App.el('div', 'bd-tip');
      if (S.phase === 1) {
        if (isCompound()) {
          tip.textContent = '点 BOSS 身上的构件，把它拆下来（'
            + S.broken.length + ' / ' + pieceCount() + '）';
        } else if (S.tier.id === 'elite') {
          tip.textContent = '构件混同的图画型古字，没有能拆的部件——先斩它的笔画（'
            + S.broken.length + ' / ' + pieceCount() + '）';
        } else {
          tip.textContent = '独体象形，身上没有构件可拆——点它的笔画，一笔一笔拆（'
            + S.broken.length + ' / ' + pieceCount() + '）';
        }
      } else if (S.phase === 2) {
        tip.textContent = isCompound()
          ? '形体错乱、构件混同——构件打法失效了。点一下它，改用笔画。'
          : '笔画糊成一片，这样拆下去没有尽头。点一下它，改用笔画。';
      } else {
        tip.textContent = '纯笔画体：一段一段斩断（' + S.cut.length + ' / ' + strokeTotal() + '）';
        tip.className = 'bd-tip final';
      }
      el.appendChild(tip);

      /* —— 战报 —— */
      var logs = App.el('div', 'bd-logs');
      S.log.forEach(function (l) {
        var row = App.el('div', 'bd-log ' + l.kind);
        row.appendChild(App.el('b', null, l.title));
        row.appendChild(App.el('span', null, l.text));
        logs.appendChild(row);
      });
      el.appendChild(logs);

      /* —— 操作 —— */
      var acts = App.el('div', 'wy-side');
      if (S.phase === 2) {
        var sw = App.el('button', 'btn primary', '改用笔画攻击');
        sw.onclick = function () { toPhase3(); };
        acts.appendChild(sw);
      }
      var redo = App.el('button', 'btn sm', '重开这一关');
      redo.onclick = function () { enter(S.idx); };
      acts.appendChild(redo);
      el.appendChild(acts);

      bindBody(sv);
    }

    /* 身体 SVG：按阶段给出不同结构（与上一版一致） */
    function bodyMarkup() {
      var b = S.boss;
      var out = [];

      if (S.phase === 3) {
        /* 终局：纯笔画体。合体 BOSS 用各构件笔画之和；其余用整字笔画。 */
        if (isCompound()) {
          var n = b.comps.length;
          b.comps.forEach(function (c, ci) {
            var cnt = App.glyphStrokeCount(c);
            for (var j = 0; j < cnt; j++) {
              var k = compIndex(ci, j);
              if (S.cut.indexOf(k) >= 0) { continue; }
              out.push('<g class="bo-cut" data-k="' + k + '" transform="' +
                compLayout(ci, n) + '">' + strokePath(c, j, 'currentColor', 1) +
                '<g class="bo-hit">' + strokePath(c, j, 'rgba(0,0,0,0)', 7) + '</g></g>');
            }
          });
        } else {
          var m = App.glyphStrokeCount(b.char);
          for (var i = 0; i < m; i++) {
            if (S.cut.indexOf(i) >= 0) { continue; }
            out.push('<g class="bo-cut" data-k="' + i + '">' +
              strokePath(b.char, i, 'currentColor', 1) +
              '<g class="bo-hit">' + strokePath(b.char, i, 'rgba(0,0,0,0)', 7) + '</g></g>');
          }
        }
        return out.join('');
      }

      /* 一、二阶段：合体拆构件；其余拆笔画 */
      if (isCompound()) {
        var nn = b.comps.length;
        b.comps.forEach(function (c, ci) {
          if (S.broken.indexOf(ci) >= 0) { return; }
          out.push('<g class="bo-part" data-k="' + ci + '" data-kind="comp" transform="' +
            compLayout(ci, nn) + '">' + App.glyphSvg(c, 'currentColor') +
            '<g class="bo-hit">' + hitAll(c, 7) + '</g>' +
            '<title>' + c + '</title></g>');
        });
        /* 已拆掉的位置留一个虚线残影 */
        b.comps.forEach(function (c, ci) {
          if (S.broken.indexOf(ci) < 0) { return; }
          out.push('<g class="bo-gone" transform="' + compLayout(ci, nn) + '">' +
            App.glyphSvg(c, 'currentColor') + '</g>');
        });
      } else {
        var cnt2 = App.glyphStrokeCount(b.char);
        for (var s = 0; s < cnt2; s++) {
          if (S.broken.indexOf(s) >= 0) { continue; }
          out.push('<g class="bo-part" data-k="' + s + '" data-kind="stroke">' +
            strokePath(b.char, s, 'currentColor', 1) +
            '<g class="bo-hit">' + strokePath(b.char, s, 'rgba(0,0,0,0)', 7) + '</g>' +
            '</g>');
        }
        for (var s2 = 0; s2 < cnt2; s2++) {
          if (S.broken.indexOf(s2) < 0) { continue; }
          out.push('<g class="bo-gone">' + strokePath(b.char, s2, 'currentColor', 1) + '</g>');
        }
      }
      return out.join('');
    }

    function bindBody(sv) {
      var b = S.boss;
      if (S.phase === 3) {
        Array.prototype.forEach.call(sv.querySelectorAll('.bo-cut'), function (g) {
          g.addEventListener('click', function () {
            var k = parseInt(g.getAttribute('data-k'), 10);
            if (S.cut.indexOf(k) >= 0) { return; }
            S.cut.push(k);
            var total = strokeTotal();
            S.hp -= 50 / total;
            if (S.cut.length >= total || S.hp <= 0) { S.hp = 0; win(); return; }
            say('cut', '斩断一段', '第 ' + S.cut.length + ' 段笔画断了——纹路护甲又少一块。');
            render();
          });
        });
        return;
      }

      Array.prototype.forEach.call(sv.querySelectorAll('.bo-part'), function (g) {
        g.addEventListener('click', function () {
          var k = parseInt(g.getAttribute('data-k'), 10);
          var kind = g.getAttribute('data-kind');
          if (S.broken.indexOf(k) >= 0) { return; }

          if (S.phase === 2) {
            if (!S.hint) {
              S.hint = true;
              say('fail', '构件打法失效', '构件已经混同、变形，拆不动了。'
                + '它化成了一团没有部件的图画——改用笔画。');
            }
            render();
            return;
          }

          /* 阶段一：拆下来，掉血，报出这个构件的能力 */
          S.broken.push(k);
          S.hp -= 50 / pieceCount();

          if (kind === 'comp') {
            var eff = effectOf(b.comps[k]);
            say('break', eff[0] + '（' + b.comps[k] + '）', eff[1]);
          } else {
            say('break', '拆去一笔', '第 ' + S.broken.length + ' 笔被拆了下来，形体轻了一分。');
          }

          if (S.broken.length >= pieceCount() || S.hp <= 0) {
            S.hp = Math.max(50, S.hp);
            S.phase = 2;
            say('fail', '构件崩坏', '它把拆散的部件又吸了回去——形体错乱、构件混同。'
              + '这正是甲骨文里那些异体乱象。构件打法继续不下去了。');
            render();
            return;
          }
          render();
        });
      });
    }

    function toPhase3() {
      S.phase = 3;
      S.cut = [];
      say('sys', '笔画终局', '它彻底化为无构件的纯图画古字。'
        + '现在只有一件事能做：把它的笔画一段一段斩断。');
      render();
    }

    function win() {
      markCleared(S.idx);
      S.view = 'win';
      say('win', '斩杀', '「' + S.boss.char + '」的纹路护甲全断，形体崩解。');
      render();
    }

    /* ============================================================
       三、通关
       ============================================================ */
    function renderWin(el) {
      var b = S.boss;
      var L = levelList();
      var last = S.idx >= L.length - 1;

      var card = App.el('div', 'bd-win');
      var sv = svgEl('svg');
      sv.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      sv.setAttribute('class', 'bd-winglyph');
      if (App.hasGlyph(b.char)) { sv.innerHTML = App.glyphSvg(b.char, 'currentColor'); }
      card.appendChild(sv);

      var info = App.el('div', 'bd-wininfo');
      /* 已经斩杀了，这里不再遮：正是要让玩家把"甲骨形 ↔ 现代字"对上 */
      info.appendChild(App.el('h3', 'bd-wintitle', '斩杀「' + b.char + '」'));
      info.appendChild(App.el('p', 'bd-windesc',
        '第 ' + (S.idx + 1) + ' 关 · ' + S.tier.name + '　' + b.note));
      if (b.comps && b.comps.length) {
        info.appendChild(App.el('p', 'bd-windesc',
          '它的身体由「' + b.comps.join('」与「') + '」拼成——拆掉其中任何一块，它都不再成形。'));
      } else {
        info.appendChild(App.el('p', 'bd-windesc',
          '全身 ' + segOf(b) + ' 段连续纹路，没有一处能拆的构件，只能用笔画破。'));
      }
      if (b.char === '車' || b.char === '虎') {
        info.appendChild(App.el('p', 'bd-winnote',
          '※ 这是本作笔画最繁的甲骨字形之一（' + segOf(b) + ' 段）。'
          + '构件拆解在它身上彻底失效——正是「繁笔破防」的由来。'));
      }
      card.appendChild(info);
      el.appendChild(card);

      var log = App.el('div', 'bd-logs');
      S.log.forEach(function (l) {
        var row = App.el('div', 'bd-log ' + l.kind);
        row.appendChild(App.el('b', null, l.title));
        row.appendChild(App.el('span', null, l.text));
        log.appendChild(row);
      });
      el.appendChild(log);

      var side = App.el('div', 'wy-side');
      if (!last) {
        var nx = App.el('button', 'btn primary', '下一关');
        nx.onclick = function () { enter(S.idx + 1); };
        side.appendChild(nx);
      } else {
        side.appendChild(App.el('span', 'chip', '全部 ' + L.length + ' 关已通关'));
      }
      var again = App.el('button', 'btn sm', '再打一次');
      again.onclick = function () { enter(S.idx); };
      side.appendChild(again);
      var tr = App.el('button', 'btn sm', '回到关卡');
      tr.onclick = function () { S.view = 'track'; S.boss = null; render(); };
      side.appendChild(tr);
      if (clearedCount() >= L.length) {
        var clr = App.el('button', 'btn sm ghost', '清空通关记录');
        clr.onclick = function () {
          if (!window.confirm('清空全部通关记录？关卡会重新锁回去。')) { return; }
          App.store.del(STORE_KEY);
          S.view = 'track'; S.boss = null;
          render();
        };
        side.appendChild(clr);
      }
      el.appendChild(side);
    }

    render();
  }

  function unmount() {
    S.view = 'track'; S.boss = null; S.tier = null; S.idx = 0;
    S.phase = 1; S.hp = 100; S.broken = []; S.cut = []; S.log = []; S.hint = false;
  }

  var total = BOSS ? (BOSS.tiers || []).reduce(function (n, t) { return n + t.list.length; }, 0) : 0;

  App.modes.register({
    id: 'boss-raid',
    name: '构件讨伐',
    tagline: '线性关卡 · 横版对战',
    desc: '二十一道关卡连成一条线，一关一关推进。身体由构件拼成的，就拆它的构件——'
        + '拆掉「止」封走位、拆掉「口」封印技能、拆掉「水」「火」消属性；'
        + '而构件混同、拆不动的图画型古字（車 17 段、虎 17 段），'
        + '只能进入笔画终局，一段一段斩断它的纹路护甲。',
    icon: '伐',
    accent: 'var(--cinnabar)',
    tags: ['线性关卡', total + ' 关', '横版对战'],
    layout: 'wide',
    minPlayers: 1, maxPlayers: 1,
    status: 'ready',
    data: { packs: [], assets: [] },
    mount: mount,
    unmount: unmount
  });

})(window.App = window.App || {});
