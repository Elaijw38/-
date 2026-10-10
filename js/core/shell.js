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
    left.appendChild(App.el('span', 'brand-sub', App.BRAND_SUB || ''));
    top.appendChild(left);

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

  /* ---------- 场景：首页 ---------- */
  function sceneHome() {
    var wrap = App.el('div', 'scene');
    wrap.appendChild(App.el('p', 'lead',
      '一个以甲骨文为题材的汉字文化游戏平台。当前已上线「甲骨构字」玩法，' +
      '后续将扩展更多玩法——它们共用同一套字形数据与素材库。'));

    var cards = App.el('div', 'home-grid');

    /* 开始游戏 */
    var c1 = App.el('div', 'home-card primary');
    c1.appendChild(App.el('span', 'hc-icon', '戏'));
    c1.appendChild(App.el('h3', null, '开始玩'));
    c1.appendChild(App.el('p', null, '选择玩法与难度，立刻开局。现有「甲骨构字」的几种模式都在里面。'));
    var wantPlay = App.el('span', 'hc-note', '');
    c1.appendChild(wantPlay);
    c1.onclick = function () { go('modes'); };
    cards.appendChild(c1);

    /* 内容管理 */
    var c2 = App.el('div', 'home-card');
    c2.appendChild(App.el('span', 'hc-icon', '包'));
    c2.appendChild(App.el('h3', null, '内容包'));
    c2.appendChild(App.el('p', null, '管理供各玩法使用的数据：字包、题库、图鉴等。'));
    var stat = App.el('span', 'hc-note', '');
    stat.textContent = App.packs.types().map(function (t) {
      return App.packs.typeMeta(t).label + ' ' + App.packs.byType(t).length;
    }).join('　·　');
    c2.appendChild(stat);
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
      card.appendChild(App.el('div', 'mc-foot', players + '　·　' +
        (m.data.packs && m.data.packs.length ? m.data.packs[0].label || '内容包' : '无特殊数据')));

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

    /* 外观 */
    var s1 = App.el('div', 'sect');
    s1.appendChild(App.el('h4', null, '外观'));
    var row = App.el('div', 'tune');
    row.appendChild(App.el('label', null, '配色'));
    var sel = App.el('select', 'mini');
    var themeList = (App.theme && App.theme.themes) ? App.theme.themes() : [
      { id: 'zhuogu', label: '灼骨（深色）' },
      { id: 'bone', label: '骨白（浅色）' },
      { id: 'plain', label: '素色（无纹理）' }
    ];
    var curTheme = (App.theme && App.theme.get) ? App.theme.get() : App.store.get('theme', 'zhuogu');
    themeList.forEach(function (t) {
      var o = document.createElement('option');
      o.value = t.id; o.textContent = t.label;
      if (curTheme === t.id) o.selected = true;
      sel.appendChild(o);
    });
    sel.onchange = function () {
      if (App.theme && App.theme.apply) App.theme.apply(sel.value);
      else { App.store.set('theme', sel.value); App.applyTheme(sel.value, App.store.get('bgimg', '')); }
    };
    row.appendChild(sel);
    s1.appendChild(row);
    var row2 = App.el('div', 'tune');
    row2.appendChild(App.el('label', null, '背景'));
    var bin = document.createElement('input');
    bin.type = 'file'; bin.accept = 'image/*'; bin.className = 'hidden';
    bin.onchange = function () {
      var f = bin.files && bin.files[0];
      if (!f) return;
      App.readScaled(f, 1600, function (url) {
        if (!url) { App.toast('背景图读取失败'); return; }
        App.store.set('bgimg', url);
        App.applyTheme(App.store.get('theme', 'bone'), url);
        App.toast('背景已更新');
      }, 'image/jpeg', 0.72);
    };
    document.body.appendChild(bin);
    var b = App.el('button', 'btn sm', '选择背景图');
    b.onclick = function () { bin.value = ''; bin.click(); };
    row2.appendChild(b);
    var bc = App.el('button', 'btn sm', '清除');
    bc.onclick = function () {
      App.store.del('bgimg');
      App.applyTheme(App.store.get('theme', 'bone'), '');
      App.toast('已恢复默认背景');
    };
    row2.appendChild(bc);
    s1.appendChild(row2);
    s1.appendChild(App.el('div', 'hint',
      '背景纹样由矢量图形生成，任何屏幕都清晰、且不加载外部图片。也可换成自己的图片（会自动淡化）。'));
    wrap.appendChild(s1);

    /* 内容包 */
    var s2 = App.el('div', 'sect');
    s2.appendChild(App.el('h4', null, '内容包'));
    s2.appendChild(App.el('div', 'hint',
      '内容包是供各玩法使用的内容数据。目前支持 ' +
      App.packs.types().map(function (t) { return App.packs.typeMeta(t).label; }).join('、') +
      '；后续玩法引入新类型时会在此出现。'));
    var tb = App.el('table', 'tl-table');
    tb.innerHTML = '<tr><th>类型</th><th>名称</th><th>内容</th><th>来源</th></tr>';
    App.packs.types().forEach(function (t) {
      App.packs.byType(t).forEach(function (p) {
        var tr = App.el('tr');
        tr.appendChild(App.el('td', null, App.packs.typeMeta(t).label));
        tr.appendChild(App.el('td', null, p.name));
        tr.appendChild(App.el('td', null, App.packs.summary(p)));
        tr.appendChild(App.el('td', null, p.builtin ? '内置' : '自建'));
        tb.appendChild(tr);
      });
    });
    s2.appendChild(tb);
    var ioBar = App.el('div', 'bar');
    var be = App.el('button', 'btn sm', '导出全部内容包');
    be.onclick = function () {
      var t = App.packs.exportAll();
      try {
        var blob = new Blob([t], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = '字趣-内容包.json';
        document.body.appendChild(a); a.click(); a.remove();
        App.toast('已导出');
      } catch (e) { App.toast('本环境不支持下载'); }
    };
    ioBar.appendChild(be);
    var bi = App.el('button', 'btn sm', '导入内容包');
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
            App.toast('导入 ' + res.added + ' 个包' + (res.skipped ? '，跳过 ' + res.skipped + ' 个' : ''));
            render();
          } catch (e) { App.toast('导入失败：' + e.message); }
        };
        r.readAsText(f);
      };
      inp.click();
    };
    ioBar.appendChild(bi);
    s2.appendChild(ioBar);
    wrap.appendChild(s2);          /* 之前漏了这一步，内容包区从未进入页面 */

    /* 存储 */
    var s3 = App.el('div', 'sect');
    s3.appendChild(App.el('h4', null, '数据与存储'));
    s3.appendChild(App.el('div', 'hint',
      '所有数据保存在本机浏览器中，不会上传到任何服务器。' +
      '换设备或清理浏览器数据后，自建内容会丢失，请用「导出」备份。'));
    var s3b = App.el('div', 'tune');
    s3b.appendChild(App.el('label', null, '已用空间'));
    s3b.appendChild(App.el('span', 'chip', (App.store.bytes() / 1024).toFixed(0) + ' KB'));
    s3b.appendChild(App.el('span', 'chip', App.store.ok() ? '本地存储可用' : '本地存储不可用（无痕模式？）'));
    s3.appendChild(s3b);
    wrap.appendChild(s3);

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
    renderHeader();
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
  App.shell = { render: render, renderHeader: renderHeader, sceneSettings: sceneSettings };

})(window.App = window.App || {});
