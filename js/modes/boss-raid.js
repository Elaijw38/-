/* ============================================================
   字趣 · 玩法模块：构件讨伐（BOSS 战）

   核心逻辑：拆字为武，组构为招，繁笔破防。

   三档 BOSS，对应三个阶段：
     一阶 合体字（涉 鸣 焚 逐 安 家）
       身体＝构件拼成（涉＝水＋止）。点构件把它从身体上拆下来。
       构件决定它的能力：止＝走位、口＝技能、水/火＝属性。拆掉即废。
     二阶 独体字（山 人 木 日 月 水）
       独体象形，身上没有构件可拆，直接拆笔画。几笔就散。
     终极 繁复字（象 龍 鳥 鼓 馬 龜 舞 車 虎）
       构件混同、拆分模糊的图画型古字（車 17 段、虎 17 段）。
       硬拆构件无效，只能斩笔画，一段一段断它的纹路护甲。

   战斗三阶段：
     一、构件压制 —— 拆构件／拆笔画，掉血
     二、构件崩坏 —— 形体错乱、构件混同，此阶段构件攻击【失效】
     三、笔画终局 —— 化为无构件的纯笔画体，斩断全部笔画即斩杀

   数据在 js/core/levels.json 的 boss 段，代码不写死任何字表。
   ============================================================ */
(function (App) {
  'use strict';

  var BOSS = (App.levels && App.levels.boss) || null;
  var SVGNS = 'http://www.w3.org/2000/svg';
  var CV = 100;

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

  var S = {
    view: 'pick', tier: null, boss: null,
    phase: 1, hp: 100, broken: [], cut: [], log: [], hint: false
  };

  function bossById(tierId, idx) {
    var t = (BOSS.tiers || []).filter(function (x) { return x.id === tierId; })[0];
    if (!t) { return null; }
    return { tier: t, data: t.list[idx] || null, idx: idx };
  }

  /* ============================================================
     挂载
     ============================================================ */
  function mount(host, ctx) {
    reset();
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
      renderPick(root);
    }

    function reset() {
      S.view = 'pick'; S.tier = null; S.boss = null;
      S.phase = 1; S.hp = 100; S.broken = []; S.cut = []; S.log = []; S.hint = false;
    }

    function say(kind, title, text) {
      S.log.unshift({ kind: kind, title: title, text: text });
      S.log = S.log.slice(0, 6);
    }

    /* ---------- 选择 BOSS ---------- */
    function renderPick(el) {
      var head = App.el('div', 'bo-head');
      head.appendChild(App.el('h3', 'bo-title', '构件讨伐'));
      head.appendChild(App.el('span', 'bo-sub', '拆字为武 · 组构为招 · 繁笔破防'));
      el.appendChild(head);
      el.appendChild(App.el('p', 'lead',
        '选一尊上古字形作为对手。身体由构件拼成的，拆构件；'
        + '构件混同、拆不动的图画型古字，只能斩笔画。'));

      (BOSS.tiers || []).forEach(function (t) {
        var sec = App.el('div', 'bo-sect');
        var h = App.el('div', 'bo-tiertitle');
        h.appendChild(App.el('span', 'bo-tiername', t.name));
        h.appendChild(App.el('span', 'bo-tiernote', t.note));
        sec.appendChild(h);
        var grid = App.el('div', 'bo-grid');
        t.list.forEach(function (b, i) {
          var card = App.el('button', 'bo-card' + (t.kind === 'compound' ? ' is-comp' : ''));
          var sv = svgEl('svg');
          sv.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
          sv.setAttribute('class', 'bo-cardglyph');
          if (t.kind === 'compound' && b.comps && b.comps.length) {
            sv.innerHTML = (b.comps || []).map(function (c, k) {
              return '<g transform="' + compLayout(k, b.comps.length) + '">' +
                App.glyphSvg(c, 'currentColor') + '</g>';
            }).join('');
          } else if (App.hasGlyph(b.char)) {
            sv.innerHTML = App.glyphSvg(b.char, 'currentColor');
          }
          card.appendChild(sv);
          card.appendChild(App.el('span', 'bo-cardname', b.char));
          var meta = (t.kind === 'compound' && b.comps && b.comps.length)
            ? b.comps.join('＋') : (b.seg + ' 笔');
          card.appendChild(App.el('span', 'bo-cardmeta', meta));
          card.onclick = function () {
            S.boss = { tier: t, data: b, idx: i };
            S.tier = t.id;
            S.view = 'fight'; S.phase = 1; S.hp = 100;
            S.broken = []; S.cut = []; S.log = []; S.hint = false;
            say('sys', '讨伐开始', '「' + b.char + '」——' + b.note);
            render();
          };
          grid.appendChild(card);
        });
        sec.appendChild(grid);
        el.appendChild(sec);
      });

      var bar = App.el('div', 'wy-side');
      var back = App.el('button', 'btn sm', '回到玩法列表');
      back.onclick = function () { ctx.nav.modes(); };
      bar.appendChild(back);
      var home = App.el('button', 'btn sm', '回到首页');
      home.onclick = function () { ctx.nav.home(); };
      bar.appendChild(home);
      el.appendChild(bar);
    }

    /* ---------- 战斗 ---------- */
    function isCompound() { return S.boss && S.boss.tier.kind === 'compound' && (S.boss.data.comps || []).length > 0; }

    /* 当前阶段要拆的「部件」总数 */
    function pieceCount() {
      var b = S.boss.data;
      if (isCompound()) { return b.comps.length; }
      return App.glyphStrokeCount(b.char) || 1;
    }
    /* 第三阶段要斩的笔画总数（合体 BOSS 用各构件笔画之和） */
    function strokeTotal() {
      var b = S.boss.data;
      if (isCompound()) {
        return (b.comps || []).reduce(function (n, c) {
          return n + (App.glyphStrokeCount(c) || 0);
        }, 0);
      }
      return App.glyphStrokeCount(b.char) || 1;
    }

    function renderFight(el) {
      var b = S.boss.data;

      var back = App.el('button', 'btn sm', '← 换一尊');
      back.onclick = function () { S.view = 'pick'; S.boss = null; render(); };
      el.appendChild(back);

      var head = App.el('div', 'bo-head');
      head.appendChild(App.el('h3', 'bo-title', '「' + b.char + '」'));
      head.appendChild(App.el('span', 'bo-sub', b.note));
      el.appendChild(head);

      /* 阶段条 */
      var phases = App.el('div', 'bo-phases');
      [['构件压制', '拆掉它的构件与笔画'],
       ['构件崩坏', '形体错乱，构件打法失效'],
       ['笔画终局', '化为纯笔画，斩断即杀']].forEach(function (p, i) {
        var d = App.el('div', 'bo-phase' + (S.phase === i + 1 ? ' on' : '') +
          (S.phase > i + 1 ? ' done' : ''));
        d.appendChild(App.el('span', 'bo-phnum', '阶段 ' + (i + 1)));
        d.appendChild(App.el('span', 'bo-phname', p[0]));
        d.appendChild(App.el('span', 'bo-phnote', p[1]));
        phases.appendChild(d);
      });
      el.appendChild(phases);

      /* HP */
      var hp = App.el('div', 'bo-hpwrap');
      hp.appendChild(App.el('span', 'bo-hplabel', 'BOSS 形体完整度'));
      var bar = App.el('span', 'bo-hpbar');
      var fill = App.el('i', 'bo-hpfill');
      fill.style.width = Math.max(0, S.hp) + '%';
      bar.appendChild(fill);
      hp.appendChild(bar);
      hp.appendChild(App.el('span', 'bo-hpnum', Math.max(0, Math.round(S.hp)) + '%'));
      el.appendChild(hp);

      /* 身体 */
      var stage = App.el('div', 'bo-stage' + (S.phase === 2 ? ' broken' : '') +
        (S.phase === 3 ? ' final' : ''));
      var sv = svgEl('svg');
      sv.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      sv.setAttribute('class', 'bo-body');
      sv.innerHTML = bodyMarkup();
      stage.appendChild(sv);
      el.appendChild(stage);

      var tip = App.el('div', 'bo-tip');
      if (S.phase === 1) {
        if (isCompound()) {
          tip.textContent = '点身体上的构件，把它拆下来（' +
            S.broken.length + ' / ' + pieceCount() + '）';
        } else if (S.tier === 'elite') {
          tip.textContent = '这是构件混同的图画型古字，没有能拆的部件——'
            + '先斩它的笔画，一段一段断（' + S.broken.length + ' / ' + pieceCount() + '）';
        } else {
          tip.textContent = '独体象形，身上没有构件可拆——点它的笔画，一笔一笔拆（' +
            S.broken.length + ' / ' + pieceCount() + '）';
        }
      } else if (S.phase === 2) {
        tip.textContent = isCompound()
          ? '形体错乱，构件混同——构件打法失效了。点一下身体，改用笔画。'
          : '形体继续错乱，笔画糊成一片——这样拆下去没有尽头。点一下身体，改用笔画。';
      } else {
        tip.textContent = '纯笔画体：一段一段斩断（' + S.cut.length + ' / ' + strokeTotal() + '）';
        tip.className = 'bo-tip final';
      }
      el.appendChild(tip);

      /* 战报 */
      var logs = App.el('div', 'bo-logs');
      S.log.forEach(function (l) {
        var row = App.el('div', 'bo-log ' + l.kind);
        row.appendChild(App.el('b', null, l.title));
        row.appendChild(App.el('span', null, l.text));
        logs.appendChild(row);
      });
      el.appendChild(logs);

      var side = App.el('div', 'wy-side');
      if (S.phase === 2) {
        var sw = App.el('button', 'btn primary', '改用笔画攻击');
        sw.onclick = function () { toPhase3(); };
        side.appendChild(sw);
      }
      var redo = App.el('button', 'btn sm', '重开这一仗');
      redo.onclick = function () {
        S.phase = 1; S.hp = 100; S.broken = []; S.cut = []; S.log = []; S.hint = false;
        say('sys', '重开', '「' + b.char + '」恢复原形，再来一次。');
        render();
      };
      side.appendChild(redo);
      el.appendChild(side);

      /* 事件绑定 */
      bindBody(sv);
    }

    /* 身体 SVG：按阶段给出不同结构 */
    function bodyMarkup() {
      var b = S.boss.data;
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

    /* 合体 BOSS 的笔画全局序号 */
    function compIndex(ci, j) {
      var n = 0;
      for (var i = 0; i < ci; i++) { n += App.glyphStrokeCount(S.boss.data.comps[i]); }
      return n + j;
    }

    /* 一个构件的全部笔画合成一条可点路径（只用于加宽热区） */
    function hitAll(c, mul) {
      var g = parts(c);
      if (!g || !g.pieces) { return ''; }
      return g.pieces.map(function (p, i) { return strokePath(c, i, 'rgba(0,0,0,0)', mul); }).join('');
    }

    function bindBody(sv) {
      var b = S.boss.data;
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
      S.view = 'win';
      say('win', '斩杀', '「' + S.boss.data.char + '」的纹路护甲全断，形体崩解。');
      render();
    }

    /* ---------- 通关 ---------- */
    function renderWin(el) {
      var b = S.boss.data;
      var card = App.el('div', 'bo-win');
      var sv = svgEl('svg');
      sv.setAttribute('viewBox', '0 0 ' + CV + ' ' + CV);
      sv.setAttribute('class', 'bo-winglyph');
      if (App.hasGlyph(b.char)) { sv.innerHTML = App.glyphSvg(b.char, 'currentColor'); }
      card.appendChild(sv);
      var info = App.el('div', 'bo-wininfo');
      info.appendChild(App.el('h3', 'bo-wintitle', '斩杀「' + b.char + '」'));
      info.appendChild(App.el('p', 'bo-windesc', b.note));
      if (b.comps && b.comps.length) {
        info.appendChild(App.el('p', 'bo-windesc',
          '它的身体由「' + b.comps.join('」与「') + '」拼成——拆掉其中任何一块，它都不再成形。'));
      } else {
        info.appendChild(App.el('p', 'bo-windesc',
          '这是独体象形字，也是笔画最繁的一类：全身 ' + b.seg +
          ' 段连续纹路，没有一处能拆的构件，只能用笔画破。'));
      }
      if (b.char === '車' || b.char === '虎') {
        info.appendChild(App.el('p', 'bo-winnote',
          '※ 这是本作笔画最繁的甲骨字形之一（' + b.seg + ' 段）。'
          + '构件拆解在它身上彻底失效——正是「繁笔破防」的由来。'));
      }
      card.appendChild(info);
      el.appendChild(card);

      var log = App.el('div', 'bo-logs');
      S.log.forEach(function (l) {
        var row = App.el('div', 'bo-log ' + l.kind);
        row.appendChild(App.el('b', null, l.title));
        row.appendChild(App.el('span', null, l.text));
        log.appendChild(row);
      });
      el.appendChild(log);

      var side = App.el('div', 'wy-side');
      var again = App.el('button', 'btn primary', '再打一次');
      again.onclick = function () {
        S.view = 'fight'; S.phase = 1; S.hp = 100; S.broken = []; S.cut = []; S.log = []; S.hint = false;
        say('sys', '重开', '「' + b.char + '」恢复原形。');
        render();
      };
      side.appendChild(again);
      var other = App.el('button', 'btn sm', '换一尊');
      other.onclick = function () { S.view = 'pick'; S.boss = null; render(); };
      side.appendChild(other);
      el.appendChild(side);
    }

    render();
  }

  function unmount() {
    S.view = 'pick'; S.boss = null; S.tier = null;
    S.phase = 1; S.hp = 100; S.broken = []; S.cut = []; S.log = []; S.hint = false;
  }

  var bossTotal = BOSS ? (BOSS.tiers || []).reduce(function (n, t) { return n + t.list.length; }, 0) : 0;

  App.modes.register({
    id: 'boss-raid',
    name: '构件讨伐',
    tagline: '拆字为武 · 组构为招 · 繁笔破防',
    desc: '与一尊上古字形对打。身体由构件拼成的，就拆它的构件——'
        + '拆掉「止」封走位、拆掉「口」封印技能、拆掉「水」「火」消属性；'
        + '而构件混同、拆不动的图画型古字（車 17 段、虎 17 段），'
        + '只能进入笔画终局，一段一段斩断它的纹路护甲。',
    icon: '伐',
    accent: 'var(--cinnabar)',
    tags: ['BOSS 战', bossTotal + ' 尊', '三阶段'],
    layout: 'wide',
    minPlayers: 1, maxPlayers: 1,
    status: 'ready',
    data: { packs: [], assets: [] },
    mount: mount,
    unmount: unmount
  });

})(window.App = window.App || {});
