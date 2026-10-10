/* 字趣 · 王邑闯关的浏览器内验证（开发自查用，不参与部署）
   由 dev/_run_wy.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   为什么直接 mount 而不走路由：
     走 location.hash 会触发壳层重渲染，中途清空并重建 #sceneRoot，
     驱动手里持有的节点引用会失效（曾因此误判地图未渲染）。
     新开宿主容器直接调 mode.mount()，可避开这类干扰，
     并能自由构造进度状态来验证解锁链。

   写法约定（血泪教训）：
     本文件曾被一次粗糙的字符串替换改坏括号，导致 Node 把错误报在下一行，
     排查时被误导了很久。因此这里保持简单、每句独立、括号一眼可数。
*/
(function () {
  'use strict';
  var L = [];
  var errs = [];
  window.addEventListener('error', function (e) {
    errs.push('ERROR: ' + e.message + ' @' + String(e.filename || '').split('/').pop() + ':' + e.lineno);
  });

  function log(s) { L.push(String(s)); }
  function q(s) { return document.querySelector(s); }
  function qa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function txt(e) { return e ? String(e.textContent).trim() : ''; }
  function has(e, c) { return !!(e && e.classList && e.classList.contains(c)); }
  function flag(b) { return b ? '是' : '否'; }

  var HOST_ID = 'wyProbeHost';

  function mountAt(progress) {
    var App = window.App;
    var old = document.getElementById(HOST_ID);
    if (old && old.parentNode) { old.parentNode.removeChild(old); }
    if (progress === null) { App.store.del('wangyi'); }
    else { App.store.set('wangyi', progress); }
    var host = document.createElement('div');
    host.id = HOST_ID;
    document.body.appendChild(host);
    var mode = App.modes.get('wangyi-map');
    mode.mount(host, App.modes.buildContext(mode));
    return host;
  }

  function cells() { return qa('#' + HOST_ID + ' .wy-cell'); }

  function zoneCell(name) {
    var list = cells();
    for (var i = 0; i < list.length; i++) {
      if (txt(list[i].querySelector('.wy-cell-name')) === name) { return list[i]; }
    }
    return null;
  }

  function cellState(c) {
    if (!c) { return '未找到'; }
    return (has(c, 'on') ? '点亮' : '未点亮') + (has(c, 'soon') ? '·筹备中' : '');
  }

  function run() {
    var App = window.App;
    try {
      log('=== 数据装载 ===');
      log('App.levels=' + flag(!!App.levels) + '  App.glyphs=' + flag(!!App.glyphs));
      log('字形数=' + Object.keys(App.glyphs.parts).length);
      log('区块数=' + App.levels.map.zones.length);
      log('模式注册=' + flag(!!App.modes.get('wangyi-map')));

      log('');
      log('=== 一、解锁链 ===');
      var cases = [
        ['无进度', null, { 自然风光: true, 动植物: false, 生产生活: false, 中央占卜坑: false }],
        ['通自然风光3关', { cleared: { landscape: ['ls-1', 'ls-2', 'ls-3'] } },
          { 自然风光: true, 动植物: false, 生产生活: false, 中央占卜坑: false }],
        ['通自然风光4关', { cleared: { landscape: ['ls-1', 'ls-2', 'ls-3', 'ls-4'] } },
          { 自然风光: true, 动植物: true, 生产生活: false, 中央占卜坑: false }],
        ['再通动植物4关', { cleared: { landscape: ['ls-1', 'ls-2', 'ls-3', 'ls-4'],
                                       creature: ['cr-1', 'cr-2', 'cr-3', 'cr-4'] } },
          { 自然风光: true, 动植物: true, 生产生活: false, 中央占卜坑: true }]
      ];
      for (var ci = 0; ci < cases.length; ci++) {
        var cs = cases[ci];
        mountAt(cs[1]);
        var names = Object.keys(cs[2]);
        var allOk = true;
        var desc = [];
        for (var ni = 0; ni < names.length; ni++) {
          var nm = names[ni];
          var on = has(zoneCell(nm), 'on');
          if (on !== cs[2][nm]) { allOk = false; }
          desc.push(nm + (on ? '亮' : '暗'));
        }
        log((allOk ? '✓ ' : '✗ ') + cs[0] + ' → ' + desc.join(' '));
        var locked = cells().filter(function (c) { return txt(c.querySelector('.wy-lock')); });
        locked.forEach(function (c) {
          log('     锁定：' + txt(c.querySelector('.wy-cell-name')) + ' — ' + txt(c.querySelector('.wy-lock')));
        });
        var soon = cells().filter(function (c) { return has(c, 'soon'); });
        soon.forEach(function (c) {
          log('     筹备中（不开放）：' + txt(c.querySelector('.wy-cell-name')));
        });
      }

      log('');
      log('=== 二、拆字机制（自然风光逐关）===');
      mountAt(null);
      var land = zoneCell('自然风光');
      land.click();
      log('关卡数=' + qa('#' + HOST_ID + ' .wy-level').length);
      var cardNames = qa('#' + HOST_ID + ' .wy-level-name').map(txt);
      log('关卡名=' + cardNames.join('、'));

      var targets = ['日', '月', '山', '水', '雨', '火'];
      var firstCard = qa('#' + HOST_ID + ' .wy-level')[0];
      firstCard.click();
      for (var k = 0; k < targets.length; k++) {
        var target = targets[k];
        var opts = qa('#' + HOST_ID + ' .wy-opt');
        var labels = opts.map(function (o) { return txt(o.querySelector('.wy-opt-name')); });
        var svgCount = qa('#' + HOST_ID + ' .wy-opt-form svg').length;
        var bigGlyph = !!q('#' + HOST_ID + ' .wy-glyph.lg svg');
        var pick = null;
        for (var oi = 0; oi < opts.length; oi++) {
          if (txt(opts[oi].querySelector('.wy-opt-name')) === target) { pick = opts[oi]; break; }
        }
        if (!pick) { log('  ✗ 第 ' + (k + 1) + ' 关选项里没有正解 ' + target + '：' + labels.join('/')); break; }
        pick.click();
        log('  第 ' + (k + 1) + ' 关 正解=' + target +
            ' 题干字形=' + flag(bigGlyph) +
            ' 选项=' + opts.length + ' 选项图形=' + svgCount +
            ' 判定=' + txt(q('#' + HOST_ID + ' .verdict')));
        var btns = qa('#' + HOST_ID + ' .bar .btn');
        var nextBtn = null;
        var backBtn = null;
        for (var bi = 0; bi < btns.length; bi++) {
          var t = txt(btns[bi]);
          if (/下一关/.test(t)) { nextBtn = btns[bi]; }
          if (/回到区块/.test(t)) { backBtn = btns[bi]; }
        }
        log('     按钮=' + btns.map(txt).join(' | '));
        if (nextBtn) {
          nextBtn.click();
          log('     → 进入下一关：' + txt(q('#' + HOST_ID + ' .wy-title')));
        } else if (backBtn) {
          backBtn.click();
          log('     → 最后一关，已回列表（卡片数=' + qa('#' + HOST_ID + ' .wy-level').length + '）');
        }
      }
      log('已过标记=' + qa('#' + HOST_ID + ' .wy-level.done').length + '/6');
      log('落盘=' + JSON.stringify(App.store.get('wangyi', null)));

      log('');
      log('=== 三、配对机制（动植物第 1 关）===');
      var prog3 = { cleared: { landscape: ['ls-1', 'ls-2', 'ls-3', 'ls-4'] } };
      mountAt(prog3);
      log('写入进度=' + JSON.stringify(prog3));
      log('读回进度=' + JSON.stringify(App.store.get('wangyi', null)));
      log('宿主存在=' + flag(!!document.getElementById(HOST_ID)));
      log('宿主节点数=' + (document.getElementById(HOST_ID) ? document.getElementById(HOST_ID).childNodes.length : -1));
      log('地图视图=' + flag(!!q('#' + HOST_ID + ' .wy-map')));
      log('区块格数=' + cells().length);
      log('区块名=' + cells().map(function (c) { return txt(c.querySelector('.wy-cell-name')); }).join('、'));
      var cr = zoneCell('动植物');
      log('动植物=' + cellState(cr) + '（应点亮）');
      cr.click();
      log('关卡数=' + qa('#' + HOST_ID + ' .wy-level').length);
      qa('#' + HOST_ID + ' .wy-level')[0].click();

      var cols = qa('#' + HOST_ID + ' .wy-pair-col');
      var leftCards = Array.prototype.slice.call(cols[0].querySelectorAll('.wy-pcard'));
      var rightCards = Array.prototype.slice.call(cols[1].querySelectorAll('.wy-pcard'));
      log('左列=' + leftCards.length + ' 右列=' + rightCards.length +
          ' 左列甲骨形=' + qa('#' + HOST_ID + ' .wy-glyph.sm svg').length);
      log('右列今字=' + rightCards.map(function (c) { return txt(c.querySelector('.wy-pchar')); }).join('/'));

      var crZone = App.levels.map.zones.filter(function (z) { return z.id === 'creature'; })[0];
      var pairs = crZone.levels[0].pairs;
      log('预期配对=' + pairs.join('/'));

      leftCards[0].click();
      log('选中左列第 1 张 → .sel=' + flag(has(leftCards[0], 'sel')));
      var wrong = null;
      for (var wi = 0; wi < rightCards.length; wi++) {
        if (txt(rightCards[wi].querySelector('.wy-pchar')) !== pairs[0]) { wrong = rightCards[wi]; break; }
      }
      wrong.click();
      log('故意配错 → 该卡 .no=' + flag(has(wrong, 'no')));

      /* 故意配错：验证即时反馈。注意产品语义是「再点同一张左卡＝取消选择」，
         所以配错之后 S.picked 仍停留在该卡上，配对循环前必须先清掉。 */
      var anyLeft = null;
      for (var li2 = 1; li2 < leftCards.length; li2++) { anyLeft = leftCards[li2]; break; }
      if (anyLeft) { anyLeft.click(); }   /* 换选一张，清掉左 0 的选择态 */
      log('配错后换选，左0 的 .sel=' + flag(has(leftCards[0], 'sel')));

      for (var pi = 0; pi < pairs.length; pi++) {
        var nm2 = pairs[pi];
        if (!has(leftCards[pi], 'sel')) { leftCards[pi].click(); }
        var selOk = has(leftCards[pi], 'sel');
        var rc = null;
        for (var ri = 0; ri < rightCards.length; ri++) {
          if (txt(rightCards[ri].querySelector('.wy-pchar')) === nm2) { rc = rightCards[ri]; break; }
        }
        if (rc) { rc.click(); }
        log('  配对 ' + nm2 + '：左列已选中=' + flag(selOk) +
            ' 找到右卡=' + flag(!!rc) +
            ' 该右卡.done=' + flag(has(rc, 'done')) +
            ' 累计完成=' + qa('#' + HOST_ID + ' .wy-pcard.done').length);
      }
      log('全部配完 → 判定=' + txt(q('#' + HOST_ID + ' .verdict')));
      log('完成卡片数=' + qa('#' + HOST_ID + ' .wy-pcard.done').length + '（4 对 = 左右各 4，共 8 张）');
      log('落盘=' + JSON.stringify(App.store.get('wangyi', null)));

      log('');
      log('=== 四、未开放区块应拦下 ===');
      mountAt(null);
      var life = zoneCell('生产生活');
      var center = zoneCell('中央占卜坑');
      log('生产生活=' + cellState(life) + '（应未点亮·筹备中）');
      log('中央占卜坑=' + cellState(center) + '（应未点亮）');
      life.click();
      log('点生产生活后仍在地图=' + flag(!!q('#' + HOST_ID + ' .wy-map')));
      center.click();
      log('点中央占卜坑后仍在地图=' + flag(!!q('#' + HOST_ID + ' .wy-map')));

      log('');
      log('=== 五、侧边入口与卸载 ===');
      var sideBtn = qa('#' + HOST_ID + ' .wy-side .btn')[0];
      log('侧边入口=' + txt(sideBtn));
      var mode = App.modes.get('wangyi-map');
      var hm = document.getElementById(HOST_ID);
      mode.unmount(hm);
      log('unmount 未抛异常=是');
      if (hm && hm.parentNode) { hm.parentNode.removeChild(hm); }
      App.store.del('wangyi');
      log('探针已清理，进度已重置');
    } catch (e) {
      log('!! 异常: ' + (e && e.message ? e.message : e));
      if (e && e.stack) {
        String(e.stack).split('\n').slice(0, 4).forEach(function (s) { log('   ' + s); });
      }
    }
    log('');
    log('=== 控制台错误 ===');
    log(errs.length ? errs.join('\n') : '(无)');
    document.documentElement.setAttribute('data-report', L.join('\n'));
  }

  var tries = 0;
  function boot() {
    tries++;
    if (window.__ZQ__ && window.App && window.App.router) { run(); return; }
    if (tries > 200) {
      log('!! 平台未就绪');
      document.documentElement.setAttribute('data-report', L.join('\n'));
      return;
    }
    setTimeout(boot, 20);
  }
  boot();
})();
