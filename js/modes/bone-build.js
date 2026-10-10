/* ============================================================
   字趣 · 玩法模块：甲骨构字
   —— 从原单文件原型迁移而来。作为平台的第一个模式接入：
      · 只通过 App.modes.register 声明自己，不触碰壳层
      · self-contained：自建 DOM、自持状态、自己管定时器
      · 通过 ctx 拿到数据包、素材库、主题与导航

   玩法要点（与原版一致）：
     翻出一张契文（字卡），玩家用构件拼出它的构件组合。
     拼对入库得分；双人模式下对手可在抢答窗口内质问抢答。
     卜问为可选的推注环节（兆吉 62%）。
   ============================================================ */
(function (App) {
  'use strict';

  /* ---------- 常量 ---------- */
  var DIFF_DEF = {
    easy:   { key:'easy',   label:'入门', pool:'easy',   timeScale:1.5,  hint:true,  divine:true,
              fastRatio:0.65, timeoutPen:1, divineRisk:false,
              desc:'只出单构件与通说两构件字，时间宽裕、可用提示' },
    normal: { key:'normal', label:'进阶', pool:'normal', timeScale:1.0,  hint:true,  divine:true,
              fastRatio:0.5,  timeoutPen:2, divineRisk:true,
              desc:'全部字卡（含待审定疑难字），标准时间与计分' },
    hard:   { key:'hard',   label:'挑战', pool:'hard',   timeScale:0.75, hint:false, divine:true,
              fastRatio:0.4,  timeoutPen:2, divineRisk:true,
              desc:'不出单构件字，时间收紧、禁用卜辞提示' }
  };
  var BASE_SEC = { one:30, twoCommon:40, twoDisputed:60 };
  var WIN_NEED = 5;          /* 字库满 5 张即结束 */

  var DIVINE = (App.data && App.data.DIVINE) || [];

  /* ---------- 工具 ---------- */
  function starsOf(card) {
    var parts = String(card.w || '').split('+').filter(Boolean);
    var n = parts.length;
    if (n <= 1) return 1;
    if (n >= 3) return 3;
    return (card.lv === '通说') ? 1 : 2;
  }
  function limitOf(card, R) {
    var parts = String(card.w || '').split('+').filter(Boolean);
    var n = parts.length;
    var base = n <= 1 ? BASE_SEC.one : (card.lv === '通说' ? BASE_SEC.twoCommon : BASE_SEC.twoDisputed);
    return Math.round(base * R.scale);
  }
  function poolFor(diff, cards) {
    var d = DIFF_DEF[diff];
    return cards.filter(function (c) {
      var n = String(c.w || '').split('+').filter(Boolean).length;
      if (d.pool === 'easy')   return c.lv === '通说' && n <= 2;
      if (d.pool === 'hard')   return n >= 2;
      return true;
    });
  }
  function catName(k) {
    var m = { natural:'自然', body:'人体', life:'动植物', object:'器物建筑', building:'器物建筑' };
    return m[k] || '其他';
  }

  /* ---------- 模式定义 ---------- */
  App.modes.register({
    id: 'bone-build',
    name: '甲骨构字',
    tagline: '用甲骨文构件拼出汉字',
    desc: '翻出契文，判断它由哪几个构件拼成。拼对即入库、得甲骨片；双人模式下对手可在倒计时里抢答质问。',
    icon: '构',
    accent: 'var(--gold)',
    tags: ['单人', '双人', '计时', '考验构形'],
    minPlayers: 1, maxPlayers: 2,
    status: 'ready',
    data: {
      packs: [{ type: 'cards', role: 'main', label: '字包' }],
      assets: []
    },
    mount: mount
  });

  /* ============================================================
     挂载
     ============================================================ */
  function mount(host, ctx) {
    var U = App, $ = U.$;
    var pack = ctx.primaryPack;
    if (!pack) { host.appendChild(U.el('p', 'lead', '没有可用的字包。')); return; }

    var CARDS = pack.data.cards.slice();
    var PIECES = pack.data.pieces.slice();

    /* ---------- 甲骨字形 ----------
       这个玩法叫「甲骨构字」，所以构件与字卡都该出真甲骨字形，
       而不是把今字换个等宽字体冒充（原先 `.g.ob` 只是
       `font-family:"Courier New"` —— 设置项写着"甲骨文"其实在骗人）。

       字形取自 js/core/glyph-parts.json（Li & Bian 数据集，CC BY 4.0）：
       37 个构件全部有真字形；34 张字卡是合体字，数据集里没有整字，
       所以用「构件组合」的方式拼出来（见 composeOracle）。 */
    var SVGNS = 'http://www.w3.org/2000/svg';
    var GLYPH_CANVAS = (App.glyphs && App.glyphs.canvas) || 100;

    function obSvg(name, size, cls) {
      if (!App.glyphSvg) return null;
      var inner = App.glyphSvg(name, 'currentColor');
      if (!inner) return null;
      var svg = document.createElementNS(SVGNS, 'svg');
      svg.setAttribute('viewBox', '0 0 ' + GLYPH_CANVAS + ' ' + GLYPH_CANVAS);
      svg.setAttribute('class', cls || 'obsvg');
      svg.setAttribute('aria-hidden', 'true');
      if (size) {
        svg.style.width = size + 'px';
        svg.style.height = size + 'px';
      }
      svg.innerHTML = inner;
      return svg;
    }

    /* 合体字的构件排布方向。
       多数甲骨合体字是左右并置；下面这些是上下相叠（屋盖在上、
       手在树上等）。这只是**示意**，不代表该字甲骨原形的精确位置——
       界面上一律标明"组合示意"，不冒充原形。 */
    var STACKED = { '家': 1, '安': 1, '灾': 1, '牢': 1, '采': 1, '集': 1, '共': 1, '兵': 1, '焚': 1 };

    /* 把合体字用【真甲骨构件】拼出来：'日+月' → 甲骨日 ＋ 甲骨月 */
    function composeOracle(card) {
      var parts = String(card.w || '').split('+').filter(Boolean);
      var have = parts.filter(function (n) { return !!App.glyphSvg(n); });
      if (!have.length) return null;
      var box = U.el('div', 'obcomp' + (STACKED[card.g] || have.length < 2 ? ' stack' : ''));
      have.forEach(function (n) {
        /* 不夹分隔符：这是"组出来的字形"，构件应当紧贴；
           "＋"式的公式说明交给判定文案（正解 宀＋火）。 */
        var s = obSvg(n, null, 'obcomp-g');
        if (s) { box.appendChild(s); } else { box.appendChild(U.el('span', 'obcomp-g', n)); }
      });
      return box;
    }

    /* ---------- 状态 ---------- */
    var S = {
      mode: 'solo',          /* solo | pvp */
      diff: 'normal',
      pieceForm: 'ob',       /* 'modern' | 'ob' —— 构件字形（ob＝真甲骨字形） */
      /* 字卡默认出今字：字卡是【题面】，若直接显示拼好的甲骨形就等于剧透答案。
         玩家要自己把甲骨构件摆进槽里组出来；答对后才揭晓组合结果。 */
      cardForm: 'modern',    /* 'modern' | 'ob' —— 字卡字形（ob＝直接给答案，慎用） */
      showLabel: true,       /* 是否显示构件名角标 */
      thinkScale: 1.0,
      winSec: 12,            /* 抢答窗口 */
      ansSec: 20,            /* 质问作答 */
      hintOn: true,
      divineOn: true,
      mask: false,
      running: false,
      over: false,
      turn: 0,
      round: 1,
      maxRound: 8,
      cur: null,
      filled: [],
      chFilled: [],
      usedCards: {},
      challenged: false,
      challengeOpen: false,
      timeline: [],
      players: [
        { name:'甲', score:0, inv:0, right:0, wrong:0, timeouts:0, timeMs:0 },
        { name:'乙', score:0, inv:0, right:0, wrong:0, timeouts:0, timeMs:0 }
      ],
      phase: '',
      timeLimit: 0
    };
    var timers = [];
    function stopTimers() {
      timers.forEach(function (t) { clearInterval(t); clearTimeout(t); });
      timers = [];
    }
    function addInterval(fn, ms) { var id = setInterval(fn, ms); timers.push(id); return id; }
    function addTimeout(fn, ms) { var id = setTimeout(fn, ms); timers.push(id); return id; }

    function P() { return S.players[S.turn]; }
    function N(i) { return S.players[i].name; }
    function R() {
      var d = DIFF_DEF[S.diff];
      return {
        scale: d.timeScale * S.thinkScale,
        fastRatio: d.fastRatio,
        timeoutPen: d.timeoutPen,
        hintOn: S.mode === 'pvp' ? (S.hintOn && d.hint) : d.hint,
        divineOn: S.divineOn && d.divine,
        divineRisk: d.divineRisk
      };
    }

    /* ---------- 壳 ---------- */
    host.appendChild(U.el('p', 'lead',
      '翻出一张契文，从构件台凑齐它的构件。拼对即入库、得甲骨片' +
      '；双人模式下对手还能在你犹豫时抢答。'));

    var setup = U.el('div', 'setup');
    host.appendChild(setup);
    var board = U.el('div', 'hidden');
    host.appendChild(board);

    /* ============================================================
       设置页
       ============================================================ */
    function buildSetup() {
      U.clearNode(setup);

      /* 1 模式 */
      var s1 = U.el('div', 'sect');
      s1.appendChild(sect('1', '选择模式'));
      var opts = U.el('div', 'opts');
      [['solo','单人练习','限时作答，答错与超时都不立即公布答案，结束时统一复盘'],
       ['pvp','双人对战','交替回合，含「质问」抢答、卜问推注、时间线复盘']]
        .forEach(function (o) {
          var d = U.el('div', 'opt' + (S.mode === o[0] ? ' on' : ''));
          d.appendChild(U.el('span', 't', o[1]));
          d.appendChild(U.el('span', 'd', o[2]));
          d.onclick = function () { S.mode = o[0]; buildSetup(); };
          opts.appendChild(d);
        });
      s1.appendChild(opts);
      setup.appendChild(s1);

      /* 2 难度 */
      var s2 = U.el('div', 'sect');
      s2.appendChild(sect('2', '选择难度'));
      var oo = U.el('div', 'opts');
      ['easy','normal','hard'].forEach(function (k) {
        var d = DIFF_DEF[k];
        var n = poolFor(k, CARDS).length;
        var el = U.el('div', 'opt' + (S.diff === k ? ' on' : ''));
        el.appendChild(U.el('span', 't', d.label));
        el.appendChild(U.el('span', 'd', d.desc + '（' + n + ' 张字卡）'));
        el.onclick = function () { S.diff = k; if (k === 'hard') S.showLabel = false; buildSetup(); };
        oo.appendChild(el);
      });
      s2.appendChild(oo);
      setup.appendChild(s2);

      /* 3 时长 */
      var s3 = U.el('div', 'sect');
      s3.appendChild(sect('3', '答题时长'));
      s3.appendChild(slider('思考时间系数', S.thinkScale, 0.5, 2, 0.05,
        function (v) { S.thinkScale = v; refresh(); },
        function (v) { return '×' + v.toFixed(2); }));
      if (S.mode === 'pvp') {
        s3.appendChild(slider('抢答窗口', S.winSec, 0, 30, 1,
          function (v) { S.winSec = v; refresh(); }, function (v) { return v + ' 秒'; }));
        s3.appendChild(slider('质问作答', S.ansSec, 5, 60, 1,
          function (v) { S.ansSec = v; refresh(); }, function (v) { return v + ' 秒'; }));
      }
      var readout = U.el('div', 'hint');
      s3.appendChild(readout);
      setup.appendChild(s3);

      /* 4 构件与字卡字形 */
      var s4 = U.el('div', 'sect');
      s4.appendChild(sect('4', '字形显示'));
      s4.appendChild(selectRow('构件字形', [['ob','真甲骨字形'], ['modern','现代字']],
        S.pieceForm, function (v) { S.pieceForm = v; refresh(); }));
      s4.appendChild(selectRow('字卡字形', [['modern','现代字（推荐）'], ['ob','甲骨形（会剧透）']],
        S.cardForm, function (v) { S.cardForm = v; refresh(); }));
      var sw = U.el('label', 'sw');
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = S.showLabel;
      cb.onchange = function () { S.showLabel = cb.checked; refresh(); };
      sw.appendChild(cb);
      sw.appendChild(document.createTextNode(' 显示构件名角标'));
      s4.appendChild(sw);
      s4.appendChild(U.el('div', 'hint',
        '构件台出真甲骨字形（取自 Li & Bian 数据集，CC BY 4.0），玩家把它们摆进槽里自己组。' +
        '字卡是【题面】，默认出今字——若让它直接显示拼好的甲骨形，就等于把答案给了。' +
        '答对（或复盘的「正解」列）才揭晓组好的甲骨形。'));
      setup.appendChild(s4);

      /* 5 对战选项 */
      if (S.mode === 'pvp') {
        var s5 = U.el('div', 'sect');
        s5.appendChild(sect('5', '对战选项'));
        s5.appendChild(checkRow('遮挡字卡（互相看不清对方在拼什么）', S.mask, function (v) { S.mask = v; }));
        s5.appendChild(checkRow('卜问推注', S.divineOn, function (v) { S.divineOn = v; }));
        s5.appendChild(checkRow('卜辞提示（−1 甲片）', S.hintOn, function (v) { S.hintOn = v; }));
        setup.appendChild(s5);
      }

      /* 开始 */
      var bar = U.el('div', 'bar');
      var start = U.el('button', 'btn primary', S.mode === 'solo' ? '开始练习' : '开始对局');
      start.onclick = startGame;
      bar.appendChild(start);
      setup.appendChild(bar);

      refresh();
      function refresh() { readout.textContent = readoutText(); }
    }
    function readoutText() {
      var n1 = Math.round(BASE_SEC.one * R().scale);
      var n2 = Math.round(BASE_SEC.twoCommon * R().scale);
      var n3 = Math.round(BASE_SEC.twoDisputed * R().scale);
      return '实际时限：单构件字 ' + n1 + 's　两构件通说 ' + n2 + 's　疑难字 ' + n3 + 's　｜　' +
        '快答需 ≤ 该字时限的 ' + Math.round(R().fastRatio * 100) + '%　｜　超时罚 −' + R().timeoutPen;
    }
    function sect(num, title) {
      var h = U.el('h4');
      h.appendChild(U.el('span', 'num', num));
      h.appendChild(document.createTextNode(title));
      return h;
    }
    function slider(label, val, lo, hi, step, onInput, fmt) {
      var w = U.el('div', 'tune');
      var lab = U.el('label', null, label);
      w.appendChild(lab);
      var inp = document.createElement('input');
      inp.type = 'range'; inp.min = lo; inp.max = hi; inp.step = step; inp.value = val;
      inp.style.flex = '1 1 auto';
      var out = U.el('span', 'chip', fmt(val));
      inp.oninput = function () { out.textContent = fmt(parseFloat(inp.value)); onInput(parseFloat(inp.value)); };
      w.appendChild(inp); w.appendChild(out);
      return w;
    }
    function selectRow(label, pairs, val, onChange) {
      var w = U.el('div', 'tune');
      w.appendChild(U.el('label', null, label));
      var sel = document.createElement('select');
      sel.className = 'mini';
      pairs.forEach(function (p) {
        var o = document.createElement('option');
        o.value = p[0]; o.textContent = p[1];
        if (val === p[0]) o.selected = true;
        sel.appendChild(o);
      });
      sel.onchange = function () { onChange(sel.value); };
      w.appendChild(sel);
      return w;
    }
    function checkRow(label, val, onChange) {
      var l = U.el('label', 'sw');
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = !!val;
      cb.onchange = function () { onChange(cb.checked); };
      l.appendChild(cb);
      l.appendChild(document.createTextNode(' ' + label));
      return l;
    }

    /* ============================================================
       对局
       ============================================================ */
    function startGame() {
      var bad = App.packs.validate(pack);
      if (bad.length) { U.toast('字包有 ' + bad.length + ' 处问题，无法开始'); return; }
      var pool = poolFor(S.diff, CARDS);
      if (pool.length < 2) { U.toast('当前难度可用字卡不足 2 张'); return; }

      S.players.forEach(function (p) {
        p.score = 0; p.inv = 0; p.right = 0; p.wrong = 0; p.timeouts = 0; p.timeMs = 0;
      });
      S.turn = 0; S.round = 1; S.over = false; S.running = true;
      S.usedCards = {}; S.timeline = [];

      buildBoard();
      setup.className = 'hidden';
      board.className = '';
      newCard();
    }

    var boardBuilt = false;
    function buildBoard() {
      if (boardBuilt) return;
      boardBuilt = true;
      U.clearNode(board);

      /* 比分板 */
      var sb = U.el('div', 'scoreboard');
      sb.id = 'mpScore';
      board.appendChild(sb);

      /* 信息条 */
      var bar = U.el('div', 'bar');
      bar.appendChild(chip('回合', '第 <b id="mpRound">1</b>/8'));
      bar.appendChild(chip('轮到', '<b id="mpTurn">甲</b>'));
      bar.appendChild(chip('难度', DIFF_DEF[S.diff].label));
      board.appendChild(bar);

      /* 计时 */
      var timer = U.el('div', 'timer');
      var tl = U.el('div', 'tl');
      tl.appendChild(U.el('span', null, '思考时间'));
      var sec = U.el('span');
      sec.appendChild(document.createTextNode('剩 '));
      var b = U.el('b', null, '0'); b.id = 'mpClock';
      sec.appendChild(b);
      sec.appendChild(document.createTextNode(' 秒'));
      tl.appendChild(sec);
      timer.appendChild(tl);
      var track = U.el('div', 'track');
      var fill = U.el('div', 'fill'); fill.id = 'mpFill';
      track.appendChild(fill);
      timer.appendChild(track);
      board.appendChild(timer);

      /* 舞台 */
      var stage = U.el('div', 'stage');
      var gb = U.el('div', 'glyphbox');
      gb.appendChild(U.el('span', 'lab', '契文'));
      var gl = U.el('span', 'glyph', ''); gl.id = 'mpGlyph';
      gb.appendChild(gl);
      /* 出甲骨形时这里显示今字，免得玩家认不出要拼哪个字 */
      var cap = U.el('span', 'glyphcap', ''); cap.id = 'mpGlyphCap';
      cap.style.display = 'none';
      gb.appendChild(cap);
      var st = U.el('span', 'star', ''); st.id = 'mpStars';
      gb.appendChild(st);
      stage.appendChild(gb);
      board.appendChild(stage);

      var info = U.el('div', 'info');
      info.appendChild(U.el('div', 'name', '请判断此字由哪几个构件拼成'));
      var mean = U.el('div', 'mean', ''); mean.id = 'mpMean';
      info.appendChild(mean);
      var slots = U.el('div', 'slots'); slots.id = 'mpSlots';
      info.appendChild(slots);
      var pbar = U.el('div', 'bar');
      var bs = U.el('button', 'btn primary', '契刻'); bs.onclick = submit;
      pbar.appendChild(bs);
      var bc = U.el('button', 'btn', '重摆'); bc.onclick = clearFill;
      pbar.appendChild(bc);
      var bh = U.el('button', 'btn sm', '卜辞提示（−1 甲片）'); bh.onclick = hint;
      pbar.appendChild(bh);
      var bch = U.el('button', 'btn danger hidden', '质问！'); bch.onclick = openChallenge;
      pbar.appendChild(bch);
      info.appendChild(pbar);
      board.appendChild(info);

      /* 质问台 */
      var cp = U.el('div', 'console hidden'); cp.id = 'mpChPanel';
      cp.appendChild(U.el('h4', null, '质问台'));
      var cd = U.el('div', 'hint', ''); cd.id = 'mpChDesc';
      cp.appendChild(cd);
      var cslots = U.el('div', 'slots'); cslots.id = 'mpChSlots';
      cp.appendChild(cslots);
      var cpad = U.el('div', 'pieces'); cpad.id = 'mpChPad';
      cp.appendChild(cpad);
      var cbar = U.el('div', 'bar');
      var cb1 = U.el('button', 'btn primary', '抢答：这就是正解'); cb1.onclick = resolveChallenge;
      cbar.appendChild(cb1);
      var cb2 = U.el('button', 'btn sm', '全部移除'); cb2.onclick = clearChallenge;
      cbar.appendChild(cb2);
      var cb3 = U.el('button', 'btn', '收回质问'); cb3.onclick = giveUpChallenge;
      cbar.appendChild(cb3);
      cp.appendChild(cbar);
      board.appendChild(cp);

      var verdict = U.el('div', 'verdict'); verdict.id = 'mpVerdict';
      board.appendChild(verdict);

      /* 卜问面板 */
      var dp = U.el('div', 'panel hidden'); dp.id = 'mpDivine';
      board.appendChild(dp);

      /* 构件台 */
      var sec = U.el('h3', 'sec', '构件台（' + PIECES.length + ' 件）');
      board.appendChild(sec);
      var pieces = U.el('div', 'pieces'); pieces.id = 'mpPieces';
      board.appendChild(pieces);

      /* 复盘区 */
      var combo = U.el('div', ''); combo.id = 'mpCombo';
      board.appendChild(combo);

      function chip(label, html) {
        var c = U.el('span', 'chip');
        c.innerHTML = label + ' ' + html;
        return c;
      }
    }

    /* ---------- 得分呈现：一律「甲骨片 ×N」 ---------- */
    /* 得分不再是一个裸数字，而是一枚甲骨片徽记加数量。
       负数保留正负号（被抢答会扣成负分）。 */
    function scoreIcon() {
      return '<span class="bone-ico" aria-hidden="true"></span>';
    }
    function ptsHTML(n) {
      var v = (n < 0 ? '−' : '') + Math.abs(n);
      return scoreIcon() + '<span class="num">' + v + '</span>' +
        '<span class="pts-unit">甲片</span>';
    }
    function ptsEl(n) {
      var d = U.el('div', 'pts');
      d.innerHTML = ptsHTML(n);
      d.title = '已得 ' + n + ' 枚甲骨片';
      return d;
    }

    /* ---------- 渲染小件 ---------- */
    function renderScore() {
      var sb = $('mpScore');
      U.clearNode(sb);
      [0, 1].forEach(function (i) {
        if (i === 1 && S.mode !== 'pvp') return;
        var p = S.players[i];
        var d = U.el('div', 'pl ' + (i === 0 ? 'p1' : 'p2'));
        if (S.turn === i && S.running) d.appendChild(U.el('span', 'tag', '轮到你了'));
        d.appendChild(U.el('div', 'who', p.name + ' · 贞人'));
        d.appendChild(ptsEl(p.score));
        var inv = U.el('div', 'inv');
        inv.innerHTML = '字库 <b>' + p.inv + '</b>/' + WIN_NEED +
          '　｜　对 <b>' + p.right + '</b>　错 <b>' + p.wrong + '</b>';
        d.appendChild(inv);
        sb.appendChild(d);
      });
      if (S.mode === 'pvp') {
        var vs = U.el('div', 'vs');
        vs.innerHTML = '对<br>局';
        sb.insertBefore(vs, sb.children[1] || null);
      }
      if ($('mpRound')) $('mpRound').textContent = String(S.round);
      if ($('mpTurn')) $('mpTurn').textContent = P().name;
    }

    function renderCard() {
      var c = S.cur;
      if (!c) return;
      var gl = $('mpGlyph');
      var ob = (S.cardForm === 'ob');
      gl.className = 'glyph' + (ob ? ' glyphob' : '');
      gl.removeAttribute('data-ob');
      U.clearNode(gl);
      var done = false;
      if (ob) {
        /* 合体字：用真甲骨构件拼出来（构件组合示意） */
        var comp = composeOracle(c);
        if (comp) { gl.appendChild(comp); done = true; }
        /* 单构件字（如「卜」）直接出整字字形 */
        if (!done) {
          var one = obSvg(c.g, null, 'glyphone');
          if (one) { gl.appendChild(one); done = true; }
        }
      }
      if (!done) { gl.textContent = c.g; }
      /* 出甲骨形时另给一行今字，避免认不出要拼哪个字 */
      var cap = $('mpGlyphCap');
      if (cap) {
        cap.textContent = (ob && done) ? c.g : '';
        cap.style.display = (ob && done) ? '' : 'none';
      }
      $('mpStars').textContent = '★'.repeat(starsOf(c));
      var lim = limitOf(c, R());
      $('mpMean').textContent = '限时 ' + lim + ' 秒　｜　用时不超 ' +
        Math.floor(lim * R().fastRatio) + ' 秒可再 ＋1' +
        (S.mode === 'pvp' ? '　｜　超时 −' + (R().timeoutPen + 1) : '');
    }

    function renderSlots() {
      var el = $('mpSlots');
      U.clearNode(el);
      var need = String(S.cur.w || '').split('+').filter(Boolean).length;
      var modern = (S.pieceForm === 'modern');
      for (var i = 0; i < Math.max(need, S.filled.length, 1); i++) {
        var d = U.el('div', 'slot');
        if (S.filled[i]) {
          d.classList.add('filled');
          var s = modern ? null : obSvg(S.filled[i], 30, 'slotsvg');
          if (s) { d.appendChild(s); } else { d.textContent = glyphOf(S.filled[i]); }
          (function (idx) {
            d.onclick = function () { S.filled.splice(idx, 1); renderSlots(); renderPieces(); };
          })(i);
        }
        el.appendChild(d);
      }
    }
    function glyphOf(name) {
      var p = PIECES.filter(function (x) { return x.n === name; })[0];
      if (!p) return name;
      if (S.pieceForm === 'modern') return p.n;
      return (p.s || p.n);
    }
    function renderPieces() {
      var box = $('mpPieces');
      U.clearNode(box);
      var modern = (S.pieceForm === 'modern');
      var label = S.showLabel !== false;
      PIECES.forEach(function (p) {
        var d = U.el('div', 'piece cat-' + (p.c || 'natural'));
        if (S.filled.indexOf(p.n) >= 0) d.classList.add('used');
        var g = U.el('span', 'g' + (modern ? '' : ' ob'));
        if (modern) {
          g.textContent = p.n;
        } else {
          /* 真甲骨字形（37 个构件全都有）；万一缺字形就退回今字 */
          var s = obSvg(p.n, 34, 'pieceob');
          if (s) { g.appendChild(s); } else { g.textContent = p.n; }
        }
        d.appendChild(g);
        /* 出甲骨形时把今字挂下面当角标，否则认不出是哪个构件 */
        if (label && !modern) d.appendChild(U.el('span', 'n', p.n));
        d.onclick = function () { addPiece(p.n); };
        box.appendChild(d);
      });
    }

    /* ---------- 计时 ---------- */
    var tickId = null, tLeft = 0, tTotal = 1;
    function startTimer(sec, onEnd) {
      stopTimer();
      tLeft = sec; tTotal = Math.max(1, sec);
      paint();
      tickId = addInterval(function () {
        tLeft -= 1;
        paint();
        if (tLeft <= 0) { var cb = onEnd; stopTimer(); if (typeof cb === 'function') cb(); }
      }, 1000);
    }
    function paint() {
      if ($('mpClock')) $('mpClock').textContent = String(Math.max(0, tLeft));
      if ($('mpFill')) $('mpFill').style.width = Math.max(0, (tLeft / tTotal) * 100) + '%';
    }
    function stopTimer() { if (tickId) { clearInterval(tickId); tickId = null; } }

    /* ---------- 发牌 ---------- */
    function newCard() {
      var pool = poolFor(S.diff, CARDS).filter(function (c) { return !S.usedCards[c.g]; });
      if (!pool.length) { endGame(); return; }
      var c = pool[Math.floor(Math.random() * pool.length)];
      S.usedCards[c.g] = 1;
      S.cur = c; S.filled = []; S.chFilled = [];
      S.challenged = false; S.challengeOpen = false;
      S.phase = 'think';
      S.startAt = Date.now();

      $('mpChPanel').className = 'console hidden';
      $('mpDivine').className = 'panel hidden';
      $('mpVerdict').className = 'verdict';
      renderCard(); renderSlots(); renderPieces(); renderScore();

      var lim = limitOf(c, R());
      S.timeLimit = lim;
      startTimer(lim, function () { onTimeout(); });
    }

    /* ---------- 拼字 ---------- */
    function addPiece(name) {
      if (!S.running || S.over) return;
      if (S.filled.indexOf(name) >= 0) return;
      var need = String(S.cur.w || '').split('+').filter(Boolean).length;
      if (S.filled.length >= need) { U.toast('已经放满 ' + need + ' 个构件了'); return; }
      S.filled.push(name);
      renderSlots(); renderPieces();
    }
    function clearFill() {
      S.filled = [];
      renderSlots(); renderPieces();
    }

    function submit() {
      if (!S.running || S.over) return;
      var c = S.cur;
      var need = String(c.w || '').split('+').filter(Boolean);
      var got = S.filled.slice();
      var ok = (got.length === need.length) &&
        need.every(function (x) { return got.indexOf(x) >= 0; });
      var used = Date.now() - S.startAt;
      var lim = S.timeLimit;
      var fast = used <= lim * 1000 * R().fastRatio;
      var star = starsOf(c);
      if (ok) {
        stopTimer();
        var gain = star + (fast ? 1 : 0);
        P().score += gain; P().inv += 1; P().right += 1; P().timeMs += used;
        record(c.g, S.turn, 'ok', need, Math.round(used / 1000), gain,
          '拼成' + (fast ? '（快答 ＋1）' : ''));
        setVerdict('ok', '✔ 拼成！正解 <b>' + need.join('＋') + '</b>　' +
          (fast ? '快答奖励 ＋1，' : '') + '共 ＋' + gain + ' 分');
        revealComposed(c);
        afterCorrect();
      } else {
        P().wrong += 1; P().timeMs += used;
        var pen = -1;
        P().score += pen;
        record(c.g, S.turn, 'wrong', need, Math.round(used / 1000), pen,
          '错答，正解：' + need.join('＋'));
        /* 单人下不立即公布答案，留到复盘 */
        setVerdict('no', S.mode === 'solo'
          ? '✘ 不对。答案留到复盘时统一公布。'
          : '✘ 不对（−1）。');
        nextTurn();
      }
    }

    function onTimeout() {
      P().timeouts += 1; P().timeMs += S.timeLimit * 1000;
      var pen = -R().timeoutPen;
      P().score += pen;
      var need = String(S.cur.w || '').split('+').filter(Boolean);
      record(S.cur.g, S.turn, 'timeout', need, S.timeLimit, pen, '超时未答');
      setVerdict('no', '⏱ 超时（' + pen + '）。');
      nextTurn();
    }

    function afterCorrect() {
      if (P().inv >= WIN_NEED) { endGame(); return; }
      /* 双人：开放抢答窗口 */
      if (S.mode === 'pvp' && S.winSec > 0) { openChallengeWindow(); return; }
      nextTurn();
    }

    function setVerdict(kind, html) {
      var v = $('mpVerdict');
      v.className = 'verdict ' + kind;
      v.innerHTML = html;
    }

    /* 答对（或复盘给出正解）后，把【玩家自己组出来的甲骨形】亮出来。
       题面不预先显示它——那是答案；这里才是"组成了"的收获时刻。 */
    function revealComposed(card) {
      var v = $('mpVerdict');
      if (!v || !card) return;
      var box = composeOracle(card);
      if (!box) return;
      var wrap = U.el('div', 'reveal');
      var t = U.el('div', 'reveal-t', '你组出的甲骨形 · 组合示意');
      wrap.appendChild(t);
      wrap.appendChild(box);
      var cap = U.el('div', 'reveal-cap', card.g);
      wrap.appendChild(cap);
      v.appendChild(wrap);
    }

    /* ---------- 质问 ---------- */
    function openChallengeWindow() {
      S.phase = 'window';
      var b = board.querySelector('.btn.danger');
      if (b) { b.className = 'btn danger'; b.innerHTML = '质问！<span id="mpChCount"></span>'; }
      var left = S.winSec;
      var upd = function () { var e = $('mpChCount'); if (e) e.textContent = '　' + left + 's'; };
      upd();
      startTimer(S.winSec, function () { closeChallengeWindow(); });
      var iv = addInterval(function () {
        left -= 1; upd();
        if (left <= 0) clearInterval(iv);
      }, 1000);
      if (b) b.onclick = openChallenge;
    }
    function closeChallengeWindow() {
      S.phase = 'defend';
      stopTimer();
      var b = board.querySelector('.btn.danger');
      if (b) b.className = 'btn danger hidden';
      nextTurn();
    }
    function openChallenge() {
      if (S.phase !== 'window') return;
      S.challengeOpen = true;
      stopTimer();
      var p = $('mpChPanel');
      p.className = 'console';
      if (document.body.classList) document.body.classList.add('challenging');
      $('mpChDesc').textContent = '你认为对方的拼法不对？在下面对出正解。';
      S.chFilled = [];
      renderChSlots();
      renderChPad();
      startTimer(S.ansSec, function () { resolveChallenge(true); });
    }
    function renderChSlots() {
      var el = $('mpChSlots');
      U.clearNode(el);
      var need = String(S.cur.w || '').split('+').filter(Boolean).length;
      for (var i = 0; i < Math.max(need, S.chFilled.length, 1); i++) {
        var d = U.el('div', 'slot');
        if (S.chFilled[i]) { d.textContent = glyphOf(S.chFilled[i]); d.classList.add('filled'); }
        el.appendChild(d);
      }
    }
    function renderChPad() {
      var box = $('mpChPad');
      U.clearNode(box);
      PIECES.forEach(function (p) {
        var d = U.el('div', 'piece cat-' + (p.c || 'natural'));
        var g = U.el('span', 'g', glyphOf(p.n));
        d.appendChild(g);
        d.onclick = function () {
          var need = String(S.cur.w || '').split('+').filter(Boolean).length;
          if (S.chFilled.length >= need) return;
          if (S.chFilled.indexOf(p.n) >= 0) return;
          S.chFilled.push(p.n); renderChSlots();
        };
        box.appendChild(d);
      });
    }
    function clearChallenge() { S.chFilled = []; renderChSlots(); }
    function giveUpChallenge() {
      stopTimer();
      $('mpChPanel').className = 'console hidden';
      if (document.body.classList) document.body.classList.remove('challenging');
      S.phase = 'defend';
      addTimeout(function () { nextTurn(); }, 400);
    }
    function resolveChallenge(timeout) {
      stopTimer();
      var need = String(S.cur.w || '').split('+').filter(Boolean);
      var got = S.chFilled.slice();
      var right = !timeout && got.length === need.length &&
        need.every(function (x) { return got.indexOf(x) >= 0; });
      var challenger = 1 - S.turn;
      var win = right ? 3 : 2;
      if (right) {
        /* 抢答成功：质问者得 win，行动方的已得分被扣回 */
        S.players[challenger].score += win;
        P().score -= win;
        record(S.cur.g, challenger, 'ch_ok', need, 0, win, '质问成功（抢答正解）');
        record(S.cur.g, S.turn, 'ch_lost', need, 0, -win, '被抢答（对手快答正解）', true);
        setVerdict('no', '⚔ 被抢答！' + N(challenger) + ' 对出正解，' +
          N(challenger) + ' ＋' + win + '，' + N(S.turn) + ' −' + win);
      } else {
        S.players[challenger].score -= 1;
        record(S.cur.g, challenger, 'ch_no', need, 0, -1, timeout ? '质问超时' : '质问失败');
        setVerdict('ok', '⚔ 质问失败。' + N(S.turn) + ' 的拼法成立。');
      }
      $('mpChPanel').className = 'console hidden';
      if (document.body.classList) document.body.classList.remove('challenging');
      renderScore();
      addTimeout(function () { nextTurn(); }, 900);
    }

    /* ---------- 提示 ---------- */
    function hint() {
      if (!R().hintOn) { U.toast('当前难度禁用卜辞提示'); return; }
      if (!S.cur) return;
      P().score -= 1;
      record(S.cur.g, S.turn, 'hint', String(S.cur.w || '').split('+'), 0, -1, '用了卜辞提示');
      var need = String(S.cur.w || '').split('+').filter(Boolean);
      setVerdict('', '卜辞提示：' + need.map(function (x) { return x.length ? x[0] + '…' : x; }).join('、') +
        '（−1 分）');
      renderScore();
    }

    /* ---------- 回合推进 ---------- */
    function nextTurn() {
      if (!S.running || S.over) return;
      S.phase = 'idle';
      if (S.mode === 'solo') {
        /* 单人：字池抽完或达 8 回合结束 */
        if (S.round >= S.maxRound ||
            Object.keys(S.usedCards).length >= poolFor(S.diff, CARDS).length) { endGame(); return; }
        S.round += 1;
        addTimeout(newCard, 700);
      } else {
        if (S.turn === 0) {
          if (S.round >= S.maxRound) { endGame(); return; }
          S.round += 1;
        }
        S.turn = 1 - S.turn;
        addTimeout(newCard, 700);
      }
    }

    function record(g, actor, result, need, sec, delta, note, noDivineAdj) {
      S.timeline.push({
        g: g, actor: N(actor), result: result,
        w: need.join('+'), sec: sec, delta: delta, note: note || '',
        noDivineAdj: !!noDivineAdj
      });
    }

    /* ---------- 结束与复盘 ---------- */
    function endGame() {
      S.running = false; S.over = true;
      stopTimer();
      board.querySelector('.stage').className = 'stage hidden';
      var timer = board.querySelector('.timer');
      if (timer) timer.className = 'timer hidden';
      var combo = $('mpCombo');
      U.clearNode(combo);

      var a = S.players[0], b = S.players[1];
      var panel = U.el('div', 'panel end');
      if (S.mode === 'solo') {
        var rank = '初学乍练';
        if (a.score >= 15) rank = '贞人 · 通神';
        else if (a.score >= 10) rank = '史官 · 博闻';
        else if (a.score >= 5) rank = '学子 · 入门';
        panel.appendChild(U.el('div', 'rank', '你的契文修养'));
        var big = U.el('div', 'score');
        big.innerHTML = ptsHTML(a.score);
        panel.appendChild(big);
        panel.appendChild(U.el('div', 'rank', rank));
        panel.appendChild(U.el('div', 'hint',
          '入库 ' + a.inv + ' 字　｜　正确 ' + a.right + '　错误 ' + a.wrong +
          '　超时 ' + a.timeouts + '　｜　累计思考 ' + U.secs(a.timeMs)));
      } else {
        var win = a.score === b.score ? '平局' : (a.score > b.score ? '甲 · 贞人 胜' : '乙 · 贞人 胜');
        panel.appendChild(U.el('div', 'rank', win));
        var row = U.el('div', 'bar');
        var c1 = U.el('span', 'chip');
        c1.innerHTML = '甲 ' + scoreIcon() + ' ' + a.score + '（入库 ' + a.inv + '）';
        row.appendChild(c1);
        var c2 = U.el('span', 'chip');
        c2.innerHTML = '乙 ' + scoreIcon() + ' ' + b.score + '（入库 ' + b.inv + '）';
        row.appendChild(c2);
        panel.appendChild(row);
      }
      var pbar = U.el('div', 'bar');
      var again = U.el('button', 'btn primary', '再契一局');
      again.onclick = function () {
        board.className = 'hidden';
        boardBuilt = false;
        setup.className = 'setup';
        buildSetup();
      };
      pbar.appendChild(again);
      var home = U.el('button', 'btn', '回到玩法列表');
      home.onclick = function () { ctx.nav.modes(); };
      pbar.appendChild(home);
      panel.appendChild(pbar);
      combo.appendChild(panel);

      /* 复盘表 */
      var rv = U.el('div', 'panel');
      rv.appendChild(U.el('h4', null, '复盘 · 每一手的用时与得失'));
      rv.appendChild(U.el('div', 'hint',
        '现在才是对答案的时候。看三件事：哪些字答错了、哪些字超时了、哪些分是被时间吃掉的。'));
      var tb = U.el('table', 'tl-table');
      tb.innerHTML = '<tr><th>#</th><th>字</th><th>谁</th><th>结果</th><th>正解</th>' +
        '<th>用时</th><th>得失</th><th>说明</th></tr>';
      S.timeline.forEach(function (r, i) {
        var tr = U.el('tr');
        tr.appendChild(U.el('td', null, String(i + 1)));
        /* 「字」列出今字（说明这一手拼的是哪个字）；
           「正解」列才揭晓 —— 用真甲骨构件把该字组出来。 */
        tr.appendChild(U.el('td', null, r.g));
        tr.appendChild(U.el('td', null, r.actor));
        var lab = { ok:'✔ 拼成', wrong:'✘ 错答', timeout:'⏱ 超时', hint:'卜辞提示',
          ch_ok:'⚔ 质问成功', ch_lost:'⚔ 被抢答', ch_no:'⚔ 质问失败' }[r.result] || r.result;
        tr.appendChild(U.el('td', null, lab));
        var tdW = U.el('td', null, '');
        var comp = S.pieceForm === 'modern' ? null : composeOracle({ g: r.g, w: r.w });
        if (comp) {
          tdW.appendChild(comp);
        } else {
          var names0 = r.w.split('+').filter(Boolean);
          names0.forEach(function (n, k) {
            if (k) { tdW.appendChild(U.el('span', 'obcomp-op', '＋')); }
            tdW.appendChild(U.el('span', null, n));
          });
        }
        tr.appendChild(tdW);
        tr.appendChild(U.el('td', null, r.sec + 's'));
        tr.appendChild(U.el('td', null, U.signed(r.delta)));
        tr.appendChild(U.el('td', null, r.note));
        tb.appendChild(tr);
      });
      rv.appendChild(tb);
      combo.appendChild(rv);
    }

    /* ---------- 挂载即建设置页 ---------- */
    buildSetup();
    ctx.nav.toString = function () { return 'bone-build'; };

    /* 卸载：清定时器与 body 上的临时类 */
    mount._unmount = function () {
      stopTimers();
      if (document.body.classList) document.body.classList.remove('challenging');
    };
    /* 把卸载挂到模式上（register 时未提供 unmount，这里补） */
    var m = App.modes.get('bone-build');
    if (m) m.unmount = mount._unmount;
  }

})(window.App = window.App || {});
