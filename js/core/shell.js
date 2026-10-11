/* ============================================================
   字趣 · 路由与壳层
   路由：#/home  #/modes  #/play/:modeId  #/settings  #/plan
   壳层负责"外部框架"（站点头、返回、底部信息、主题），
   场景负责"内容"（首页、模式选择、设置、对局）。
   模式只拿到一个空容器 host，不感知壳层结构 —— 这是可插拔的关键。
   ============================================================ */
(function (App) {
  'use strict';

  var root = null;          /* 场景挂载点 */
  var current = { name: '', params: {} };
  var currentMode = null;   /* 正在运行的模式对象 */

  /* ---------- 工具 ---------- */
  function go(name, params, replace) {
    var h = '#/' + name + (params && params.id ? '/' + params.id : '');
    if (replace) location.replace(h); else location.hash = h;
  }
  function replay() {
    var h = location.hash;
    location.hash = '';
    setTimeout(function () { location.hash = h; }, 30);
  }

  /* ---------- 顶部导航 ----------
     品牌 + 四个入口 + 右侧操作。
     改版前是"首页无导航、内页左侧功能栏"；需求要求固定顶部导航，
     于是取消左侧栏，统一成一条顶栏，窄屏由 CSS 折成两行。 */
  var NAV_ITEMS = [
    { id: 'home',  label: '主页' },
    { id: 'modes', label: '开始游戏' },
    { id: 'atlas', label: '汉字图鉴' },
    { id: 'howto', label: '玩法说明' }
  ];

  function navActiveId() {
    switch (current.name) {
      case 'home':  return 'home';
      case 'modes': return 'modes';
      case 'play':  return 'modes';      /* 对局属于「开始游戏」分支 */
      case 'atlas': return 'atlas';
      case 'howto': return 'howto';
      case 'plan':  return 'howto';      /* 「后续玩法」并入玩法说明 */
      case 'settings': return 'settings';
      default: return '';
    }
  }

  /* 品牌标识：甲骨字形 + 艺术字，整块可点回首页 */
  function brandNode() {
    var brand = App.el('a', 'top-brand');
    brand.href = '#/home';
    var img = App.el('img', 'brand-glyph');
    img.alt = ''; img.setAttribute('aria-hidden', 'true');
    img.src = App.brandGlyphURI || '';
    brand.appendChild(img);
    var art = App.el('span', 'brand-art');
    art.setAttribute('aria-hidden', 'true');
    ['构', '字', '记'].forEach(function (ch) { art.appendChild(App.el('span', 'ch', ch)); });
    brand.appendChild(art);
    brand.appendChild(App.el('span', 'sr-only', '字趣 · 甲骨构字记'));
    return brand;
  }

  function renderHeader() {
    var top = App.$('siteTop');
    if (!top) return;
    App.clearNode(top);

    top.appendChild(brandNode());

    var act = navActiveId();
    var nav = App.el('nav', 'top-nav');
    nav.setAttribute('aria-label', '主导航');
    NAV_ITEMS.forEach(function (it) {
      var a = App.el('a', 'top-link' + (act === it.id ? ' on' : ''));
      a.href = '#/' + it.id;
      a.textContent = it.label;
      if (act === it.id) a.setAttribute('aria-current', 'page');
      nav.appendChild(a);
    });
    top.appendChild(nav);

    var right = App.el('div', 'top-right');
    right.appendChild(App.el('span', 'seal top-seal', App.BRAND_SEAL || '试玩版'));
    var set = App.el('a', 'top-link top-set' + (act === 'settings' ? ' on' : ''), '设置');
    set.href = '#/settings';
    set.setAttribute('aria-label', '设置与备份');
    right.appendChild(set);
    top.appendChild(right);
  }

  /* 左侧功能栏已取消。这个函数保留成空操作：
     App.shell.renderNav 是对外暴露过的接口，留着避免调用方报错。 */
  function renderNav() {}

  /* ---------- 页脚 ---------- */
  function renderFooter() {
    var list = App.$('footModes');
    if (list) {
      App.clearNode(list);
      App.modes.playable().forEach(function (m) {
        var li = App.el('li', 'foot-item');
        var a = App.el('a', null, m.name);
        a.href = '#/play/' + m.id;
        li.appendChild(a);
        if (m.tagline) li.appendChild(App.el('span', 'foot-tag', m.tagline));
        list.appendChild(li);
      });
      var liMore = App.el('li', 'foot-item');
      var aMore = App.el('a', null, '汉字图鉴');
      aMore.href = '#/atlas';
      liMore.appendChild(aMore);
      liMore.appendChild(App.el('span', 'foot-tag', '按字查看来处'));
      list.appendChild(liMore);
    }
    var v = App.$('footVer');
    if (v) v.textContent = App.BRAND_VERSION || '';
  }

  /* ---------- 常用小件 ---------- */
  var SVGNS = 'http://www.w3.org/2000/svg';

  /* 一个装了真甲骨字形的 SVG。没有这个字形时返回 null —— 宁可不画，也不画假的。 */
  function glyphSvgNode(ch, cls) {
    if (!App.hasGlyph(ch)) { return null; }
    var sv = document.createElementNS(SVGNS, 'svg');
    sv.setAttribute('viewBox', '0 0 100 100');
    sv.setAttribute('class', cls || 'obglyph');
    sv.setAttribute('role', 'img');
    sv.setAttribute('aria-label', '甲骨文「' + ch + '」');
    sv.innerHTML = App.glyphSvg(ch, 'currentColor');
    return sv;
  }

  /* 合体字的"甲骨组合示意"。
     数据集里这些合体字没有整字甲骨形（这是真实情况，不编造）；
     但它们的构件都有真字形——按「甲骨构字」那套把构件并排拼成示意形。
     必须说清是"组合示意"，不能让它看起来像一个整字字形。 */
  function compSvgNode(comps, cls) {
    var list = (comps || []).filter(function (c) { return App.hasGlyph(c); });
    if (!list.length) { return null; }
    var n = list.length;
    var sv = document.createElementNS(SVGNS, 'svg');
    sv.setAttribute('viewBox', '0 0 100 100');
    sv.setAttribute('class', cls || 'obglyph');
    sv.setAttribute('role', 'img');
    sv.setAttribute('aria-label', '甲骨构件组合示意：' + list.join(' ＋ '));
    var s = 1 / n;
    sv.innerHTML = list.map(function (c, k) {
      return '<g transform="translate(' + (k * 100 * s).toFixed(3) + ',0) scale(' +
        s.toFixed(5) + ')">' + App.glyphSvg(c, 'currentColor') + '</g>';
    }).join('');
    return sv;
  }

  /* 取一个字的显示用字形：优先整字真字形，退而用构件组合示意，都没有才返回 null */
  function anyGlyphNode(e, cls) {
    return glyphSvgNode(e.char, cls) || compSvgNode(e.comps, cls);
  }

  /* 区块标题：左标题+说明，右"更多" */
  function sectionHead(title, note, href, moreLabel) {
    var h = App.el('div', 'sec-head');
    var l = App.el('div', 'sec-head-l');
    l.appendChild(App.el('h2', 'sec-h', title));
    if (note) l.appendChild(App.el('p', 'sec-note', note));
    h.appendChild(l);
    if (href) {
      var a = App.el('a', 'sec-more', moreLabel || '更多');
      a.href = href;
      h.appendChild(a);
    }
    return h;
  }

  /* 某个玩法玩到哪了。没有进度可报的返回 null，
     不编造一个 0% 出来充数（甲骨构字目前不落盘进度）。 */
  function modeProgress(m) {
    if (m.id === 'wangyi-map') {
      var all = 0;
      (((App.levels || {}).map || {}).zones || []).forEach(function (z) {
        all += (z.objects || []).length;
      });
      var n = 0;
      var wy = App.store.get('wangyi', null);
      if (wy && wy.done) {
        for (var z2 in wy.done) {
          if (wy.done.hasOwnProperty(z2)) { n += (wy.done[z2] || []).length; }
        }
      }
      return { now: n, all: all, label: '已点亮' };
    }
    if (m.id === 'boss-raid') {
      var total = 0;
      (((App.levels || {}).boss || {}).tiers || []).forEach(function (t2) {
        total += (t2.list || []).length;
      });
      var bo = App.store.get('bossraid', null);
      var n2 = (bo && bo.cleared) ? bo.cleared.length : 0;
      return { now: n2, all: total, label: '已通关' };
    }
    return null;
  }

  function progressBar(p) {
    var wrap = App.el('div', 'pc-prog');
    var bar = App.el('span', 'pc-progbar');
    var fill = App.el('i', 'pc-progfill');
    fill.style.width = (p.all ? Math.round(p.now / p.all * 100) : 0) + '%';
    bar.appendChild(fill);
    wrap.appendChild(bar);
    wrap.appendChild(App.el('span', 'pc-progtext', p.label + ' ' + p.now + ' / ' + p.all));
    return wrap;
  }

  /* ---------- 场景：首页 ---------- */
  function sceneHome() {
    var wrap = App.el('div', 'scene home-scene');
    var st = App.atlas.stats();
    var daily = App.atlas.daily();

    /* ================= 首屏：一屏大图 =================
       骨片居中放大，标题与 CTA 在下方居中，整块占满一屏；
       再往下滚（或点底部的「下滑看玩法」）才是「选择你的玩法」。 */
    var hero = App.el('section', 'hero');
    var hin = App.el('div', 'hero-in');   /* 只装文字，背景在它下面 */

    /* 实物直接铺满整块当背景。
       这张原片本身就是暗底（骨片居中、四周深色展柜），
       压一层薄纱把文字托出来即可，不必把照片压得看不见。
       来源 Gary Todd，CC0 1.0 公有领域（法律上无需署名，仍照标）。 */
    var bg = App.el('img', 'hero-bg');
    bg.src = 'assets/oracle-bone.jpg';
    bg.alt = '';
    bg.setAttribute('aria-hidden', 'true');
    hero.appendChild(bg);
    hero.appendChild(App.el('div', 'hero-veil'));

    var hb = App.el('div', 'hero-body');
    hb.appendChild(App.el('p', 'hero-kicker', '甲骨文 · 汉字文化互动'));
    hb.appendChild(App.el('h1', 'hero-title', '三千年前的汉字，等你来发现'));
    hb.appendChild(App.el('p', 'hero-lead',
      '看字形 · 猜字义 · 解构汉字的起源。把甲骨文的字形本身做成玩法，'
      + '每一个字都能追到它由哪些构件拼成、刻在哪一片卜辞上。'));

    var cta = App.el('div', 'hero-cta');
    var b1 = App.el('a', 'btn primary lg hero-main');
    b1.href = '#/modes';
    b1.appendChild(App.el('span', null, '开始探索'));
    b1.appendChild(App.el('span', 'hero-arrow', '→'));
    cta.appendChild(b1);
    var b2 = App.el('a', 'btn lg hero-ghost', '先看图鉴');
    b2.href = '#/atlas';
    cta.appendChild(b2);
    hb.appendChild(cta);
    hb.appendChild(App.el('p', 'hero-trust', '无需注册 · 即点即玩 · 进度存在本机'));
    hin.appendChild(hb);

    hero.appendChild(hin);

    /* 下滑提示：点了平滑滚到「选择你的玩法」，
       与"自己往下滚"是同一件事的两个入口。 */
    var cue = App.el('button', 'hero-cue', '下滑看玩法');
    cue.appendChild(App.el('span', 'hero-cue-arrow', '↓'));
    cue.onclick = function () {
      var target = App.$('playSection');
      if (!target) { return; }
      if (target.scrollIntoView) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        window.scrollTo(0, target.offsetTop);
      }
    };
    hero.appendChild(cue);

    /* 署名：压在右下角小字。CC0 不强制署名，但出处该写清楚。 */
    var cap = App.el('p', 'hero-credit');
    cap.appendChild(App.el('span', 'hc-name', '骨片刻辞 · 商代'));
    cap.appendChild(App.el('span', 'hc-src',
      '摄影 Gary Todd　CC0 1.0 公有领域　Wikimedia Commons'));
    hero.appendChild(cap);

    wrap.appendChild(hero);

    /* 数字用真实的：字形数、构件数、字卡数、玩法数。
       放在首屏**下面**——首屏要留给那张大图，数据是滚下来才看的。 */
    var glyphCount = Object.keys((App.glyphs || {}).parts || {}).length;
    var pieceCount = ((App.data || {}).BUILTIN_PIECES || []).length;
    var poolCount = ((App.data || {}).BUILTIN_POOL || []).length;
    var band = App.el('ul', 'stat-band');
    [[glyphCount, '个甲骨字形'], [pieceCount, '个构件'],
     [poolCount, '张识字字卡'], [App.modes.playable().length, '个玩法']]
      .forEach(function (x) {
        var li = App.el('li', 'stat-cell');
        li.appendChild(App.el('b', null, String(x[0])));
        li.appendChild(App.el('span', null, x[1]));
        band.appendChild(li);
      });
    wrap.appendChild(band);

    /* ================= 核心玩法 ================= */
    var sec1 = App.el('section', 'home-sec');
    sec1.id = 'playSection';
    sec1.appendChild(sectionHead('选择你的玩法',
      '三个玩法共用同一套字形数据与素材库，各有各的节奏',
      '#/modes', '全部玩法 →'));
    var grid = App.el('div', 'play-grid');
    App.modes.playable().forEach(function (m) {
      var card = App.el('a', 'play-card');
      card.href = '#/play/' + m.id;

      var head = App.el('div', 'pc-head');
      var ico = App.el('span', 'pc-icon', m.icon);
      ico.style.background = m.accent || 'var(--cinnabar)';
      head.appendChild(ico);
      var ttl = App.el('div', 'pc-title');
      ttl.appendChild(App.el('h3', null, m.name));
      if (m.tagline) ttl.appendChild(App.el('span', 'pc-tagline', m.tagline));
      head.appendChild(ttl);
      card.appendChild(head);

      if (m.desc) card.appendChild(App.el('p', 'pc-desc', m.desc));
      if (m.tags && m.tags.length) {
        var tg = App.el('div', 'pc-tags');
        m.tags.forEach(function (x) { tg.appendChild(App.el('span', 'tag', x)); });
        card.appendChild(tg);
      }
      var pr = modeProgress(m);
      if (pr && pr.all) card.appendChild(progressBar(pr));
      card.appendChild(App.el('span', 'pc-go', '进入 →'));
      grid.appendChild(card);
    });
    sec1.appendChild(grid);
    wrap.appendChild(sec1);

    /* ================= 内容探索 ================= */
    var sec2 = App.el('section', 'home-sec');
    sec2.appendChild(sectionHead('内容探索',
      '每天认识一个字，也能对照查一查它的来处', '#/atlas', '进入图鉴 →'));
    var row = App.el('div', 'explore-grid');

    /* 每日一字 */
    var dc = App.el('article', 'daily-card');
    var dh = App.el('div', 'dc-head');
    dh.appendChild(App.el('h3', 'dc-title', '每日一字'));
    dh.appendChild(App.el('span', 'dc-date', daily ? daily.date : ''));
    dc.appendChild(dh);
    if (daily) {
      var dbody = App.el('div', 'dc-body');
      var box = App.el('div', 'dc-ob');
      /* 合体字没有整字甲骨形（真实情况），退用构件组合示意，
         否则这里会是个空框。 */
      var composed = !App.hasGlyph(daily.char) && daily.comps.length > 0;
      var g = anyGlyphNode({ char: daily.char, comps: daily.comps },
                           'dc-glyph' + (composed ? ' composed' : ''));
      if (g) box.appendChild(g);
      else box.appendChild(App.el('span', 'ac-noglyph', '暂无字形'));
      if (composed) box.appendChild(App.el('span', 'dc-composednote', '组合示意'));
      dbody.appendChild(box);
      var info = App.el('div', 'dc-info');
      /* 现代字单独放在标了"今字"的格子里，不压在甲骨形上 */
      var pair = App.el('div', 'dc-pair');
      pair.appendChild(App.el('span', 'dc-lab', '今字'));
      pair.appendChild(App.el('span', 'dc-char', daily.char));
      info.appendChild(pair);
      if (daily.comps.length) {
        var cp = App.el('div', 'dc-pair');
        cp.appendChild(App.el('span', 'dc-lab', '构件'));
        cp.appendChild(App.el('span', 'dc-comps', daily.comps.join(' ＋ ')));
        info.appendChild(cp);
      }
      info.appendChild(App.el('p', 'dc-mean', daily.meaning));
      if (daily.source) info.appendChild(App.el('p', 'dc-src', '卜辞：' + daily.source));
      dbody.appendChild(info);
      dc.appendChild(dbody);
    } else {
      dc.appendChild(App.el('p', 'lead', '字卡数据缺失。'));
    }
    row.appendChild(dc);

    /* 收集进度 */
    var sum = App.achievements ? App.achievements.summary() : null;
    var cc = App.el('article', 'collect-card');
    var ch2 = App.el('div', 'dc-head');
    ch2.appendChild(App.el('h3', 'dc-title', '我的收集'));
    ch2.appendChild(App.el('span', 'dc-date', '存在本机'));
    cc.appendChild(ch2);
    var cbody = App.el('div', 'cc-body');
    /* 评级：由收集度换算的称号，对应甲骨学里的身份 */
    if (sum) {
      var rk = App.el('div', 'cc-rank');
      rk.appendChild(App.el('span', 'cc-ranklab', '当前评级'));
      rk.appendChild(App.el('b', 'cc-rankname', sum.rank.name));
      rk.appendChild(App.el('span', 'cc-ranknote', sum.rank.note));
      cbody.appendChild(rk);
    }
    var big = App.el('div', 'cc-big');
    big.appendChild(App.el('b', null, String(st.learned)));
    big.appendChild(App.el('span', null, ' / ' + st.chars + ' 个字'));
    cbody.appendChild(big);
    var cbar = App.el('span', 'cc-bar');
    var cfill = App.el('i', 'cc-fill');
    cfill.style.width = st.percent + '%';
    cbar.appendChild(cfill);
    cbody.appendChild(cbar);
    var kinds = App.el('ul', 'cc-kinds');
    App.atlas.KINDS.forEach(function (k) {
      var b = st.byKind[k.id] || { total: 0, learned: 0 };
      var li = App.el('li', 'cc-kind');
      li.appendChild(App.el('span', 'cc-kname', k.name));
      li.appendChild(App.el('span', 'cc-knum', b.learned + ' / ' + b.total));
      kinds.appendChild(li);
    });
    cbody.appendChild(kinds);
    if (sum && sum.nextRank && st.learned) {
      cbody.appendChild(App.el('p', 'cc-note',
        '再收 ' + Math.max(0, sum.nextNeed - st.learned) + ' 个字，可升「'
        + sum.nextRank.name + '」。'));
    } else {
      cbody.appendChild(App.el('p', 'cc-note',
        st.learned ? '三个玩法里学会的字都会记进这里。'
                   : '还没开始收集——去图卷上点亮第一个实物，或进图鉴看看有哪些字。'));
    }
    var cgo = App.el('a', 'btn primary', '进入图鉴');
    cgo.href = '#/atlas';
    cbody.appendChild(cgo);
    cc.appendChild(cbody);
    row.appendChild(cc);

    sec2.appendChild(row);
    if (App.achievements) { sec2.appendChild(achieveCard()); }
    wrap.appendChild(sec2);

    return wrap;
  }

  /* 成就墙：每项都从真实进度算，未达成的显示进度条而不是灰掉了事 */
  function achieveCard() {
    var sum = App.achievements.summary();
    var list = App.achievements.list();
    var card = App.el('article', 'ach-card');
    var h = App.el('div', 'dc-head');
    h.appendChild(App.el('h3', 'dc-title', '我的成就'));
    h.appendChild(App.el('span', 'dc-date',
      '已达成 ' + sum.achieved + ' / ' + sum.total));
    card.appendChild(h);

    var grid = App.el('div', 'ach-grid');
    list.forEach(function (a) {
      var it = App.el('div', 'ach-item' + (a.done ? ' done' : ''));
      var ico = App.el('span', 'ach-icon', a.icon);
      it.appendChild(ico);
      var body = App.el('div', 'ach-body');
      var top = App.el('div', 'ach-top');
      top.appendChild(App.el('b', 'ach-name', a.name));
      if (a.done) { top.appendChild(App.el('span', 'ach-mark', '已达成')); }
      body.appendChild(top);
      body.appendChild(App.el('span', 'ach-desc', a.desc));
      var bar = App.el('span', 'ach-bar');
      var fill = App.el('i', 'ach-fill');
      fill.style.width = a.percent + '%';
      bar.appendChild(fill);
      body.appendChild(bar);
      body.appendChild(App.el('span', 'ach-num', a.now + ' / ' + a.need));
      it.appendChild(body);
      grid.appendChild(it);
    });
    card.appendChild(grid);
    return card;
  }

  /* ---------- 场景：汉字图鉴 ----------
     四档真实内容汇总成一张表；筛选状态放在模块级，
     这样页面内切换筛选不必重走整个路由。 */
  var atlasFilter = { kind: 'all', q: '' };

  function sceneAtlas() {
    var wrap = App.el('div', 'scene atlas-scene');
    var st = App.atlas.stats();

    var head = App.el('div', 'atlas-head');
    var l = App.el('div', 'sec-head-l');
    l.appendChild(App.el('h1', 'sec-h', '汉字图鉴'));
    l.appendChild(App.el('p', 'sec-note',
      '这里的字形都来自本项目使用的开源甲骨字形数据集，按字查它的构件与来处。'));
    head.appendChild(l);
    var prog = App.el('div', 'atlas-prog');
    prog.appendChild(App.el('b', null, String(st.learned)));
    prog.appendChild(App.el('span', null, ' / ' + st.chars + ' 已解锁'));
    head.appendChild(prog);
    wrap.appendChild(head);

    /* 筛选条 */
    var bar = App.el('div', 'atlas-bar');
    var tabs = App.el('div', 'atlas-tabs');
    /* 片子上的数字一律用**条目数**，这样"牌子写几，点进去就有几条"。
       去重后的字数（102）留在页头「已解锁 x / 102」，那里讲的就是字数。 */
    var allEntries = App.atlas.entries().length;
    var gotEntries = App.atlas.entries().filter(function (e) {
      return st.learnedSet[e.char];
    }).length;

    var allBtn = App.el('button', 'chipbtn', '全部 ' + allEntries);
    tabs.appendChild(allBtn);
    var gotBtn = App.el('button', 'chipbtn', '已解锁 ' + gotEntries);
    gotBtn.setAttribute('data-kind', 'got');
    tabs.appendChild(gotBtn);
    App.atlas.KINDS.forEach(function (k) {
      /* byKind 的 total 本来就是条目数，与点击结果一致，保持 */
      var b = st.byKind[k.id] || { total: 0, learned: 0 };
      var btn = App.el('button', 'chipbtn', k.name + ' ' + b.total);
      btn.setAttribute('data-kind', k.id);
      tabs.appendChild(btn);
    });
    bar.appendChild(tabs);

    var search = App.el('input', 'atlas-search');
    search.type = 'search';
    search.placeholder = '按字、构件或释义找…';
    search.value = atlasFilter.q;
    search.setAttribute('aria-label', '在图鉴里检索');
    bar.appendChild(search);
    wrap.appendChild(bar);

    var count = App.el('p', 'atlas-count');
    wrap.appendChild(count);
    var grid = App.el('div', 'atlas-grid');
    wrap.appendChild(grid);

    function paint() {
      Array.prototype.forEach.call(tabs.children, function (b) {
        var k = b.getAttribute('data-kind') || 'all';
        b.className = 'chipbtn' + (atlasFilter.kind === k ? ' on' : '');
      });
      var q = atlasFilter.q.trim().toLowerCase();
      var learn = st.learnedSet;
      var list = App.atlas.entries().filter(function (e) {
        if (atlasFilter.kind === 'got' && !learn[e.char]) return false;
        if (atlasFilter.kind !== 'all' && atlasFilter.kind !== 'got'
            && e.kind !== atlasFilter.kind) return false;
        if (!q) return true;
        var hay = [e.char, (e.comps || []).join(''), e.meaning || '',
                   e.source || '', e.zone || '', e.tier || '', e.cat || ''].join(' ').toLowerCase();
        return hay.indexOf(q) >= 0;
      });
      App.clearNode(grid);
      count.textContent = '共 ' + list.length + ' 条'
        + (atlasFilter.kind === 'all' ? '' : '（' + atlasFilter.kind + '）')
        + (q ? '　筛选：「' + atlasFilter.q + '」' : '');
      if (!list.length) {
        grid.appendChild(App.el('p', 'lead', atlasFilter.kind === 'got'
          ? '还没有解锁任何字。去玩一局——点亮、通关、答对都会记进这里。'
          : '没有匹配的字。换个关键词，或点上面的「全部」。'));
        return;
      }
      list.forEach(function (e) {
        var card = App.el('button', 'atlas-card' + (learn[e.char] ? ' got' : ''));
        card.setAttribute('aria-label', '甲骨文「' + e.char + '」，点击查看详情');
        var box = App.el('div', 'ac-ob');
        var isComposed = !e.hasGlyph && (e.comps || []).length > 0;
        var g = anyGlyphNode(e, 'ac-glyph' + (isComposed ? ' composed' : ''));
        if (g) box.appendChild(g);
        else box.appendChild(App.el('span', 'ac-noglyph', '无字形'));
        /* 与游戏里一致：现代字默认不印在甲骨形上，
           指针落上去或键盘聚焦才浅浅浮出 */
        box.appendChild(App.el('span', 'ac-char', e.char));
        card.appendChild(box);
        card.appendChild(App.el('span', 'ac-kind',
          kindName(e.kind) + (isComposed ? '　组合' : '')));
        card.onclick = function () { openAtlasDetail(e); };
        grid.appendChild(card);
      });
    }

    allBtn.onclick = function () { atlasFilter.kind = 'all'; paint(); };
    Array.prototype.forEach.call(tabs.children, function (b) {
      if (!b.getAttribute('data-kind')) return;
      b.onclick = function () {
        atlasFilter.kind = b.getAttribute('data-kind');
        paint();
      };
    });
    search.oninput = function () { atlasFilter.q = search.value; paint(); };

    paint();
    return wrap;
  }

  function kindName(id) {
    var k = App.atlas.KINDS.filter(function (x) { return x.id === id; })[0];
    return k ? k.name : id;
  }

  /* 图鉴详情：底部抽屉式的浮层（窄屏铺满，宽屏居中） */
  function openAtlasDetail(e) {
    var old = App.$('atlasSheet');
    if (old && old.parentNode) old.parentNode.removeChild(old);

    var mask = App.el('div', 'overlay atlas-mask');
    mask.id = 'atlasSheet';
    var box = App.el('div', 'edbox atlas-sheet');

    var hd = App.el('div', 'edhead');
    hd.appendChild(App.el('h3', null, '「' + e.char + '」'));
    hd.appendChild(App.el('span', 'as-kind', kindName(e.kind)));
    var close = App.el('button', 'btn sm ghost as-close', '关闭');
    close.onclick = function () { if (mask.parentNode) mask.parentNode.removeChild(mask); };
    hd.appendChild(close);
    box.appendChild(hd);

    var body = App.el('div', 'edbody as-body');
    var left = App.el('div', 'as-left');
    var g = anyGlyphNode(e, 'as-glyph');
    if (g) left.appendChild(g);
    left.appendChild(App.el('span', 'as-char', e.char));
    left.appendChild(App.el('span', 'as-charlab', '今字'));
    if (!e.hasGlyph && (e.comps || []).length) {
      left.appendChild(App.el('span', 'as-composednote', '构件组合示意'));
    }
    body.appendChild(left);

    var right = App.el('div', 'as-right');
    if (e.comps && e.comps.length) {
      right.appendChild(App.el('p', 'as-line',
        '构件：' + e.comps.join(' ＋ ') + '（' + e.comps.length + ' 块）'));
    }
    if (e.meaning) right.appendChild(App.el('p', 'as-line', '释义：' + e.meaning));
    if (e.source) right.appendChild(App.el('p', 'as-line as-src', '卜辞出处：' + e.source));
    if (e.zone) right.appendChild(App.el('p', 'as-line', '在王邑图卷上属于：' + e.zone));
    if (e.tier) right.appendChild(App.el('p', 'as-line', '构件讨伐：' + e.tier));
    if (e.cat) right.appendChild(App.el('p', 'as-line', '构件分类：' + e.cat));
    if (e.level) right.appendChild(App.el('p', 'as-line', '字卡等级：' + e.level));
    if (e.seg) right.appendChild(App.el('p', 'as-line', '字形笔画段数：' + e.seg + ' 段'));

    /* 这个字在哪些玩法里出现过——都指到真入口 */
    var apps = App.atlas.appearancesOf(e.char);
    var links = App.el('div', 'as-links');
    if (apps.some(function (x) { return x.kind === 'object'; })) {
      var a1 = App.el('a', 'btn sm', '去王邑点亮它');
      a1.href = '#/play/wangyi-map';
      links.appendChild(a1);
    }
    if (apps.some(function (x) { return x.kind === 'boss'; })) {
      var a2 = App.el('a', 'btn sm', '去讨伐它');
      a2.href = '#/play/boss-raid';
      links.appendChild(a2);
    }
    if (apps.some(function (x) { return x.kind === 'piece'; })) {
      var a3 = App.el('a', 'btn sm', '拿它去构字');
      a3.href = '#/play/bone-build';
      links.appendChild(a3);
    }
    if (links.children.length) right.appendChild(links);

    var isLearned = !!App.atlas.learned()[e.char];
    right.appendChild(App.el('p', 'as-state' + (isLearned ? ' got' : ''),
      isLearned ? '已在你的收集里' : '尚未解锁——去玩一局就会记进来'));
    body.appendChild(right);
    box.appendChild(body);

    mask.appendChild(box);
    mask.onclick = function (ev) { if (ev.target === mask) close.onclick(); };
    document.body.appendChild(mask);
    close.focus();
  }

  /* ---------- 场景：玩法说明 ---------- */
  function sceneHowto() {
    var wrap = App.el('div', 'scene howto-scene');

    var head = App.el('div', 'sec-head-l');
    head.appendChild(App.el('h1', 'sec-h', '玩法说明'));
    head.appendChild(App.el('p', 'sec-note',
      '三个玩法的规则、操作与要点。共用的那套字形数据在页脚有署名。'));
    wrap.appendChild(head);

    var list = App.modes.playable().map(function (m) {
      return {
        id: m.id, name: m.name, tagline: m.tagline, desc: m.desc,
        icon: m.icon, accent: m.accent, tags: m.tags || [],
        steps: HOWTO[m.id] || []
      };
    });

    list.forEach(function (m, idx) {
      var sec = App.el('section', 'howto-sec');
      var h = App.el('div', 'howto-head');
      var ico = App.el('span', 'pc-icon', m.icon);
      ico.style.background = m.accent || 'var(--cinnabar)';
      h.appendChild(ico);
      var ttl = App.el('div', 'pc-title');
      ttl.appendChild(App.el('h2', 'howto-name', (idx + 1) + '．' + m.name));
      if (m.tagline) ttl.appendChild(App.el('span', 'pc-tagline', m.tagline));
      h.appendChild(ttl);
      var go2 = App.el('a', 'btn sm primary', '进入玩法');
      go2.href = '#/play/' + m.id;
      h.appendChild(go2);
      sec.appendChild(h);
      if (m.desc) sec.appendChild(App.el('p', 'howto-desc', m.desc));

      if (m.steps.length) {
        var ol = App.el('ol', 'howto-steps');
        m.steps.forEach(function (s) {
          var li = App.el('li');
          li.appendChild(App.el('b', null, s[0]));
          li.appendChild(App.el('span', null, s[1]));
          ol.appendChild(li);
        });
        sec.appendChild(ol);
      }
      if (m.tags.length) {
        var tg = App.el('div', 'howto-tags');
        m.tags.forEach(function (x) { tg.appendChild(App.el('span', 'tag', x)); });
        sec.appendChild(tg);
      }
      wrap.appendChild(sec);
    });

    /* 通用操作提示 */
    var tips = App.el('section', 'howto-sec howto-tips');
    tips.appendChild(App.el('h2', 'howto-name', '通用操作'));
    var tl = App.el('ul', 'howto-list');
    [
      ['鼠标', '点一下就是选中；带悬停提示的地方，把指针放上去就能看到名字与说明。'],
      ['触屏', '直接点按；需要"悬停才出现"的内容，按住不放同样会显示。'],
      ['键盘', 'Tab 可以在可点元素之间移动，回车/空格选中；焦点所在处有朱砂描边。'],
      ['进度', '点亮记录、通关记录都存在本机浏览器里，不上传服务器；换设备前记得在「设置」里导出备份。']
    ].forEach(function (x) {
      var li = App.el('li');
      li.appendChild(App.el('b', null, x[0]));
      li.appendChild(App.el('span', null, x[1]));
      tl.appendChild(li);
    });
    tips.appendChild(tl);
    wrap.appendChild(tips);

    /* 后续玩法（原来单独一页，现并入说明） */
    var planned = App.modes.all().filter(function (m) { return m.status !== 'ready'; });
    var next = App.el('section', 'howto-sec');
    next.appendChild(App.el('h2', 'howto-name', '后续玩法'));
    next.appendChild(App.el('p', 'howto-desc', planned.length
      ? '平台已预留扩展位。新玩法会作为独立模块加入，与现有玩法共用同一套字形数据。'
      : '平台已预留扩展位，新玩法会作为独立模块加入。'));
    if (planned.length) {
      var pl = App.el('ul', 'howto-list');
      planned.forEach(function (m) {
        var li = App.el('li');
        li.appendChild(App.el('b', null, m.name));
        li.appendChild(App.el('span', null, (m.tagline || '') + (m.desc ? '　' + m.desc : '')));
        pl.appendChild(li);
      });
      next.appendChild(pl);
    }
    wrap.appendChild(next);

    /* 资料来源与授权 —— 与页脚一致，这里写全 */
    var src = App.el('section', 'howto-sec');
    src.appendChild(App.el('h2', 'howto-name', '资料来源与授权'));
    var sl = App.el('ul', 'howto-list');
    [
      ['甲骨字形', 'Oracle Bone Glyphs: Parametric Vector Dataset v0.3，'
        + '数据 CC BY 4.0、代码 MIT，本项目做缩放、配色与合成。'],
      ['底图', '殷商王邑图卷由 Agnes AI 生成，无第三方水印。'],
      ['说明', '字形用于识字对照，不代表原简拓片的笔迹；'
        + '概不外推为学术结论，教学演示用途。']
    ].forEach(function (x) {
      var li = App.el('li');
      li.appendChild(App.el('b', null, x[0]));
      li.appendChild(App.el('span', null, x[1]));
      sl.appendChild(li);
    });
    src.appendChild(sl);
    wrap.appendChild(src);

    return wrap;
  }

  /* 每个玩法在说明页要讲的几步。文案对应各模块里真实的规则，不额外发明机制。 */
  var HOWTO = {
    'bone-build': [
      ['翻契文', '屏幕上方给出一段甲骨字形（契文）。'],
      ['判断构件', '看它由哪几块构件拼成——构件台里有真甲骨字形可对照。'],
      ['拼字', '把构件拖到放置槽，位置对了才会吸附。'],
      ['得甲片', '拼对即入账，结算里能看到这个字的构件与释义。'],
      ['双人模式', '对手可以在倒计时里抢答，比谁先拼出来。']
    ],
    'wangyi-map': [
      ['一幅灰图', '整幅殷商王邑图卷初始是灰的。'],
      ['点实物', '点图上的实物热区，认出它对应的字。'],
      ['构字', '上面给甲骨文原字，下面给笔画，拖到正确位置拼出来。'],
      ['点亮', '拼成一个字，地图上那一块就亮起来。'],
      ['一键点亮', '演示或展示时，可以一次点亮全部 61 处。']
    ],
    'boss-raid': [
      ['一条线走到底', '21 道关卡沿一枚甲骨片的轮廓推进，通关才解锁下一关。'],
      ['阶段一 · 构件压制', '合体字档从构件池里自己挑构件砸上去；挑错记误选，不扣血。'],
      ['阶段二 · 构件崩坏', '形体错乱、构件混同，这一手失效。'],
      ['阶段三 · 笔画终局', '化成纯笔画体，一段一段斩断即斩杀。'],
      ['复杂的直接拆笔画', '独体字与繁复字身上没有可拆的构件，直接点它拆笔画。'],
      ['完美通关', '一次都没挑错，珠子会描金。']
    ]
  };

  /* ---------- 场景：模式选择 ---------- */
  function sceneModes() {
    var wrap = App.el('div', 'scene');
    wrap.appendChild(App.el('p', 'lead', '选一个玩法。每个玩法有各自的规则与节奏，但共用同一套字形数据与素材库。'));

    var list = App.modes.playable();
    var groupReady = App.el('div', 'mode-grid');
    var groupPlan = App.el('div', 'mode-grid');

    list.forEach(function (m) {
      var card = App.el('div', 'mode-card' + (m.status !== 'ready' ? ' pending' : ''));
      var head = App.el('div', 'mc-head');
      var ico = App.el('span', 'mc-icon', m.icon);
      ico.style.background = m.accent;
      head.appendChild(ico);
      var ttl = App.el('div', 'mc-title');
      ttl.appendChild(App.el('h3', null, m.name));
      ttl.appendChild(App.el('span', 'mc-tagline', m.tagline));
      head.appendChild(ttl);
      if (m.status === 'planning') head.appendChild(App.el('span', 'mc-badge', '筹备中'));
      if (m.status === 'wip') head.appendChild(App.el('span', 'mc-badge', '开发中'));
      card.appendChild(head);
      if (m.desc) card.appendChild(App.el('p', 'mc-desc', m.desc));
      if (m.tags.length) {
        var tg = App.el('div', 'mc-tags');
        m.tags.forEach(function (t) { tg.appendChild(App.el('span', 'tag', t)); });
        card.appendChild(tg);
      }
      var players = m.maxPlayers > 1 ? (m.minPlayers + '—' + m.maxPlayers + ' 人') : '单人';
      /* 声明了内容包才显示它的名字；没声明的就不显示，
         不要写「无特殊数据」——那是把内部概念漏到界面上。 */
      var packLabel = (m.data.packs && m.data.packs.length)
        ? (m.data.packs[0].label || '') : '';
      card.appendChild(App.el('div', 'mc-foot',
        players + (packLabel ? '　·　' + packLabel : '')));

      if (m.status === 'ready') {
        card.onclick = function () { App.store.set('lastMode', m.id); go('play', { id: m.id }); };
      } else {
        card.onclick = function () { App.toast('「' + m.name + '」还在筹备中。'); };
      }
      (m.status === 'ready' ? groupReady : groupPlan).appendChild(card);
    });

    if (groupReady.children.length) wrap.appendChild(groupReady);
    if (groupPlan.children.length) {
      wrap.appendChild(App.el('h3', 'sec-title', '筹备中的玩法（已预留）'));
      wrap.appendChild(groupPlan);
    }
    return wrap;
  }

  /* ---------- 场景：筹备中玩法说明 ---------- */
  function scenePlan() {
    var wrap = App.el('div', 'scene');
    wrap.appendChild(App.el('p', 'lead',
      '这个平台不是只为一款游戏准备的。下面是已经预留、后续会加入的玩法位；' +
      '新增玩法只需加一个模块文件，不必改动平台的其它部分。'));

    var tb = App.el('table', 'tl-table');
    tb.innerHTML = '<tr><th>玩法</th><th>状态</th><th>说明</th></tr>';
    App.modes.all().forEach(function (m) {
      var tr = App.el('tr');
      tr.appendChild(App.el('td', null, m.name));
      tr.appendChild(App.el('td', null,
        m.status === 'ready' ? '已上线' : (m.status === 'wip' ? '开发中' : '筹备中')));
      tr.appendChild(App.el('td', null, m.desc || m.tagline || ''));
      tb.appendChild(tr);
    });
    wrap.appendChild(tb);
    return wrap;
  }

  /* ---------- 场景：全局设置 ---------- */
  function sceneSettings() {
    var wrap = App.el('div', 'scene');
    wrap.appendChild(App.el('p', 'lead', '这里的设置对所有玩法生效。玩法自己的选项在开局前设置。'));

    /* 数据备份
       原先这里是「内容包」区块：一张只有一行的表（内置字包）+ 导出/导入。
       表已删（用户既改不了也加不了内容），导出/导入移到这里——
       它是唯一的备份途径，不能跟着界面一起删掉。 */
    var s2 = App.el('div', 'sect');
    s2.appendChild(App.el('h4', null, '数据备份'));
    s2.appendChild(App.el('div', 'hint',
      '进度、设置与自建内容都保存在本机浏览器里，不会上传到任何服务器。' +
      '换设备或清理浏览器数据前，先导出备份。'));
    var s2b = App.el('div', 'tune');
    s2b.appendChild(App.el('label', null, '已用空间'));
    s2b.appendChild(App.el('span', 'chip', (App.store.bytes() / 1024).toFixed(0) + ' KB'));
    s2b.appendChild(App.el('span', 'chip', App.store.ok() ? '本地存储可用' : '本地存储不可用（无痕模式？）'));
    s2.appendChild(s2b);

    var ioBar = App.el('div', 'bar');
    var be = App.el('button', 'btn sm', '导出备份');
    be.onclick = function () {
      var t = App.packs.exportAll();
      try {
        var blob = new Blob([t], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = '字趣-备份.json';
        document.body.appendChild(a); a.click(); a.remove();
        App.toast('已导出');
      } catch (e) { App.toast('本环境不支持下载'); }
    };
    ioBar.appendChild(be);
    var bi = App.el('button', 'btn sm', '导入备份');
    bi.onclick = function () {
      var inp = document.createElement('input');
      inp.type = 'file'; inp.accept = '.json,application/json';
      inp.onchange = function () {
        var f = inp.files && inp.files[0];
        if (!f) return;
        var r = new FileReader();
        r.onload = function () {
          try {
            var res = App.packs.importText(String(r.result));
            App.toast('已导入 ' + res.added + ' 项' + (res.skipped ? '，跳过 ' + res.skipped + ' 个' : ''));
            render();
          } catch (e) { App.toast('导入失败：' + e.message); }
        };
        r.readAsText(f);
      };
      inp.click();
    };
    ioBar.appendChild(bi);
    s2.appendChild(ioBar);
    wrap.appendChild(s2);


    return wrap;
  }

  /* ---------- 场景：对局（交给模式） ---------- */
  function scenePlay(modeId) {
    var mode = App.modes.get(modeId);
    if (!mode) {
      var e = App.el('div', 'scene');
      e.appendChild(App.el('p', 'lead', '找不到这个玩法。'));
      var bb = App.el('button', 'btn', '回到玩法列表');
      bb.onclick = function () { go('modes'); };
      e.appendChild(bb);
      return e;
    }
    var wrap = App.el('div', 'scene play-scene');
    /* 宽屏玩法：模式在描述里声明 layout:'wide'，内容就占满整个界面
       （王邑图卷与构件讨伐是主打，整幅画要铺满，不能缩在限宽栏里）。
       类加在 .app-shell 上；下一次 render 会在设 className 时自动清掉。 */
    if (mode.layout === 'wide') {
      wrap.classList.add('scene-wide');
      var sh = App.$('appShell');
      if (sh) { sh.classList.add('layout-wide'); }
    }
    var bar = App.el('div', 'play-bar');
    var back = App.el('button', 'btn sm', '← 返回');
    back.onclick = function () {
      if (currentMode && currentMode.unmount) { try { currentMode.unmount(host); } catch (e) {} }
      currentMode = null;
      go('modes');
    };
    bar.appendChild(back);
    bar.appendChild(App.el('span', 'chip', mode.name));
    bar.appendChild(App.el('span', 'play-spacer'));
    var again = App.el('button', 'btn sm', '重开');
    again.onclick = function () {
      if (currentMode && currentMode.unmount) { try { currentMode.unmount(host); } catch (e) {} }
      currentMode = null;
      replay();
    };
    bar.appendChild(again);
    wrap.appendChild(bar);

    var host = App.el('div', 'mode-host');
    wrap.appendChild(host);
    /* 同步挂载：模式在 host 进入文档之前就构建好 DOM，
       这对模式内部没有影响（它只操作自己那棵子树），
       但能让"渲染完成"与"路由切换"在同一帧内结束，避免出现空壳瞬间。 */
    if (!mode.mount) {
      host.appendChild(App.el('p', 'lead', '该玩法尚未实现。'));
    } else {
      currentMode = mode;
      try {
        mode.mount(host, App.modes.buildContext(mode));
      } catch (err) {
        host.appendChild(App.el('p', 'lead', '玩法加载出错：' + err.message));
        if (window.console && console.error) console.error('[字趣] 玩法挂载失败', err);
      }
    }
    return wrap;
  }

  /* ---------- 渲染 ---------- */
  function parseHash() {
    var h = (location.hash || '').replace(/^#\/?/, '');
    var seg = h.split('/').filter(Boolean);
    return { name: seg[0] || 'home', params: { id: seg[1] || '' } };
  }
  function render() {
    var r = parseHash();
    /* 离开对局时先卸载上一个模式，避免定时器残留 */
    if (current.name === 'play' && (r.name !== 'play' || r.params.id !== current.params.id)) {
      if (currentMode && currentMode.unmount) { try { currentMode.unmount(App.$('modeHost')); } catch (e) {} }
      currentMode = null;
    }
    current = r;
    App.clearNode(root);
    /* 首页单列居中；进入页面后切为「左功能栏 + 右内容」两栏 */
    var shell = App.$('appShell');
    if (shell) shell.className = 'app-shell scene-' + r.name;
    /* 固定顶部导航：不再有"首页单列 / 内页侧栏"的切换，
       data-nav 固定为 top，保留属性是为了 CSS 钩子与旧样式兼容。 */
    document.body.setAttribute('data-nav', 'top');
    if (document.body.classList) {
      document.body.classList.remove('nav-single', 'nav-side');
      document.body.classList.add('nav-top');
    }
    renderHeader();
    renderFooter();
    /* 新达成的成就：回壳层时对一次账。
       不在玩法里埋钩子（那要改三个模块），玩家玩完总要走某条路由。 */
    if (App.achievements) {
      var fresh = App.achievements.check();
      if (fresh.length) {
        App.toast('成就达成 · ' + fresh.map(function (a) {
          return '「' + a.name + '」';
        }).join(''));
      }
    }
    var scene;
    if (r.name === 'modes') scene = sceneModes();
    else if (r.name === 'play') scene = scenePlay(r.params.id);
    else if (r.name === 'settings') scene = sceneSettings();
    else if (r.name === 'atlas') scene = sceneAtlas();
    else if (r.name === 'howto' || r.name === 'plan') scene = sceneHowto();
    else scene = sceneHome();
    root.appendChild(scene);
    window.scrollTo(0, 0);
    App.emit('route', r);
  }

  function start() {
    root = App.$('sceneRoot');
    if (!root) { console.error('缺少 #sceneRoot'); return; }
    window.addEventListener('hashchange', render);
    render();
  }

  App.router = { go: go, replay: replay, render: render, start: start, current: function () { return current; } };
  App.shell = {
    render: render, renderHeader: renderHeader, renderNav: renderNav,
    renderFooter: renderFooter, sceneSettings: sceneSettings,
    sceneHome: sceneHome, sceneAtlas: sceneAtlas, sceneHowto: sceneHowto
  };

})(window.App = window.App || {});
