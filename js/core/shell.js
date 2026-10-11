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

  /* ---------- 站点头 ---------- */
  function renderHeader() {
    var top = App.$('siteTop');
    if (!top) return;
    App.clearNode(top);

    var left = App.el('div', 'top-left');
    var h1 = App.el('h1', 'brand');
    var img = App.el('img', 'brand-glyph');
    img.alt = ''; img.setAttribute('aria-hidden', 'true');
    img.src = App.brandGlyphURI || '';
    h1.appendChild(img);
    var art = App.el('span', 'brand-art');
    art.setAttribute('aria-hidden', 'true');
    ['构', '字', '记'].forEach(function (ch) {
      art.appendChild(App.el('span', 'ch', ch));
    });
    h1.appendChild(art);
    h1.appendChild(App.el('span', 'sr-only', '甲骨构字记'));
    left.appendChild(h1);
    /* 首页整块居中，副标题交给场景里的导语承担，这里不重复 */
    if (current.name !== 'home') {
      left.appendChild(App.el('span', 'brand-sub', App.BRAND_SUB || ''));
    }
    top.appendChild(left);

    /* 首页只留品牌居中；内页的返回与设置入口都在左侧功能栏里 */
    if (current.name === 'home') return;

    var right = App.el('div', 'top-right');
    var seal = App.el('span', 'seal', App.BRAND_SEAL || '试玩版');
    right.appendChild(seal);
    if (current.name !== 'settings') {
      var b1 = App.el('button', 'btn sm', '全局设置');
      b1.onclick = function () { go('settings'); };
      right.appendChild(b1);
    } else {
      var b0 = App.el('button', 'btn sm', '返回');
      b0.onclick = function () { go('home'); };
      right.appendChild(b0);
    }
    top.appendChild(right);
  }

  /* ---------- 左侧功能栏 ---------- */
  function navActiveId() {
    switch (current.name) {
      case 'home':     return 'home';
      case 'modes':    return 'modes';
      case 'plan':     return 'plan';
      case 'settings': return 'settings';
      case 'play':     return 'modes';      /* 对局属于「开始玩」分支 */
      default:         return '';
    }
  }

  function navItem(item) {
    var a = App.el('a', 'nav-item');
    a.href = '#/' + item.id;
    if (navActiveId() === item.id) a.className += ' on';
    a.appendChild(App.el('span', 'nav-ico', item.icon));
    a.appendChild(App.el('span', 'nav-label', item.label));
    return a;
  }

  function renderNav() {
    var host = App.$('siteNav');
    if (!host) return;
    App.clearNode(host);

    /* 品牌 */
    var brand = App.el('div', 'nav-brand');
    var img = App.el('img', 'brand-glyph');
    img.alt = ''; img.setAttribute('aria-hidden', 'true');
    img.src = App.brandGlyphURI || '';
    brand.appendChild(img);
    var art = App.el('span', 'brand-art');
    art.setAttribute('aria-hidden', 'true');
    ['构', '字', '记'].forEach(function (ch) {
      art.appendChild(App.el('span', 'ch', ch));
    });
    brand.appendChild(art);
    brand.appendChild(App.el('span', 'sr-only', '甲骨构字记'));
    /* 侧栏里的品牌可点回首页 */
    brand.style.cursor = 'pointer';
    brand.onclick = function () { go('home'); };
    host.appendChild(brand);

    host.appendChild(App.el('div', 'nav-sub', App.BRAND_SUB || ''));

    /* 与首页三张卡一一对应 */
    [
      { id: 'home',     icon: '首', label: '首　页' },
      { id: 'modes',    icon: '戏', label: '开始玩' },
      { id: 'plan',     icon: '续', label: '后续玩法' },
      { id: 'settings', icon: '设', label: '设置与备份' }
    ].forEach(function (it) { host.appendChild(navItem(it)); });

    /* 底部：试玩版印章 + 版本号 */
    var foot = App.el('div', 'nav-foot');
    foot.appendChild(App.el('span', 'seal', App.BRAND_SEAL || '试玩版'));
    foot.appendChild(App.el('span', 'nav-ver', 'v' + (App.BRAND_VERSION || '')));
    host.appendChild(foot);
  }

  /* ---------- 场景：首页 ---------- */
  function sceneHome() {
    var wrap = App.el('div', 'scene home-scene');
    wrap.appendChild(App.el('p', 'lead home-lead',
      '一个以甲骨文为题材的汉字文化游戏平台。现有「殷商王邑」（图卷点亮 · 构字）、' +
      '「甲骨构字」（拼字 · 卜问 · 质问）与「构件讨伐」（拆构件打 BOSS）三个玩法，' +
      '共用同一套字形数据与素材库。'));

    var cards = App.el('div', 'home-grid');

    /* 开始游戏 */
    var c1 = App.el('div', 'home-card primary');
    c1.appendChild(App.el('span', 'hc-icon', '戏'));
    c1.appendChild(App.el('h3', null, '开始玩'));
    c1.appendChild(App.el('p', null, '选择玩法与难度，立刻开局。'));
    var wantPlay = App.el('span', 'hc-note', '');
    c1.appendChild(wantPlay);
    c1.onclick = function () { go('modes'); };
    cards.appendChild(c1);

    /* 说明与备份
       原先这里还有一张「内容包」卡，只显示「字包 1 · 题库 0 · 图鉴 0 · 章节 0」
       —— 三个 0 看着像没做完（那三类只有类型定义、既无内容也无添加入口）。
       App.packs 数据层仍在（甲骨构字靠它拿字卡），只是不再拿它当首页卖点。 */
    var c2 = App.el('div', 'home-card');
    c2.appendChild(App.el('span', 'hc-icon', '备'));
    c2.appendChild(App.el('h3', null, '数据备份'));
    c2.appendChild(App.el('p', null, '进度与设置都存在本机浏览器里。换设备或清理浏览器数据前，先导出备份。'));
    var note2 = App.el('span', 'hc-note', '');
    note2.textContent = '已用 ' + (App.store.bytes() / 1024).toFixed(0) + ' KB';
    c2.appendChild(note2);
    c2.onclick = function () { go('settings'); };
    cards.appendChild(c2);

    /* 未来玩法 */
    var planned = App.modes.all().filter(function (m) { return m.status === 'planning'; });
    var c3 = App.el('div', 'home-card ghost');
    c3.appendChild(App.el('span', 'hc-icon', '续'));
    c3.appendChild(App.el('h3', null, '后续玩法'));
    c3.appendChild(App.el('p', null, planned.length
      ? '已预留 ' + planned.length + ' 个玩法位：' +
        planned.map(function (m) { return m.name; }).join('、')
      : '平台已预留扩展位，新玩法会作为独立模块加入。'));
    c3.onclick = function () { go('plan'); };
    cards.appendChild(c3);

    wrap.appendChild(cards);
    return wrap;
  }

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
    /* 宽屏玩法：模式在描述里声明 layout:'wide'，内容就占满整个界面——
       侧栏让位、去掉 .app-main 的 900px 限宽。
       （王邑图卷是主打玩法，整幅画要铺满，不能缩在右半边的角落里。）
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
    var mode = (r.name === 'home') ? 'single' : 'side';
    document.body.setAttribute('data-nav', mode);
    if (document.body.classList) {
      document.body.classList.toggle('nav-single', mode === 'single');
      document.body.classList.toggle('nav-side', mode === 'side');
    }
    renderHeader();
    renderNav();
    var scene;
    if (r.name === 'modes') scene = sceneModes();
    else if (r.name === 'play') scene = scenePlay(r.params.id);
    else if (r.name === 'settings') scene = sceneSettings();
    else if (r.name === 'plan') scene = scenePlan();
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
  App.shell = { render: render, renderHeader: renderHeader, renderNav: renderNav, sceneSettings: sceneSettings };

})(window.App = window.App || {});
