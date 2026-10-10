/* 字趣 · 王邑图卷（点亮 + 构字）的浏览器内验证 —— 开发自查，不参与部署
   由 dev/_run_wy.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   验两条主线：
     1) 点亮：地图初始是灰的（底层灰度 + 上层彩色被 mask 遮住），
        每拼成一个字，mask 里多一个白圆 → 那一块变彩色。
     2) 构字：点实物 → 上给甲骨文原字、下给笔画 → 拖到正确位置 → 拼成。

   硬约束（都踩过）：
     · SVG 无 .click()，要派发事件。
     · 每次 render 会 clearNode 重建 DOM，动作前必须重新查询节点。
     · 全程同步，不用 setTimeout 排队（会与 --virtual-time-budget 互触发而挂死）。
     · 拖拽要派发 pointerdown/move/up，且事件要打在挂监听的那个元素上。
*/
(function () {
  'use strict';
  var L = [], errs = [];
  window.addEventListener('error', function (e) {
    errs.push('ERROR: ' + e.message + ' @' + String(e.filename || '').split('/').pop() + ':' + e.lineno);
  });
  function log(s) { L.push(String(s)); }
  function q(s) { return document.querySelector(s); }
  function qa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function txt(e) { return e ? String(e.textContent).trim() : ''; }
  function flag(b) { return b ? '是' : '否'; }
  var HOST_ID = 'wyProbeHost';
  function H(s) { return '#' + HOST_ID + ' ' + s; }

  function tap(el) {
    if (!el) return false;
    if (typeof el.click === 'function') { el.click(); return true; }
    var ev = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
    el.dispatchEvent(ev);
    return true;
  }
  function btnByText(re) {
    var l = qa(H('button'));
    for (var i = 0; i < l.length; i++) { if (re.test(txt(l[i]))) return l[i]; }
    return null;
  }
  function spots() { return qa(H('.wy-spot')); }
  function spotByChar(ch) {
    var l = spots();
    for (var i = 0; i < l.length; i++) {
      var al = l[i].getAttribute('aria-label') || '';
      if (al.indexOf(ch + '，') === 0) return l[i];
    }
    return null;
  }
  function mountFresh() {
    var App = window.App;
    var old = document.getElementById(HOST_ID);
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var host = document.createElement('div');
    host.id = HOST_ID;
    document.body.appendChild(host);
    var m = App.modes.get('wangyi-map');
    m.mount(host, App.modes.buildContext(m));
  }

  /* 把画布坐标(0~100)换成屏幕坐标，再往部件上派发拖拽事件 */
  function dragTo(box, canvasPt) {
    var stage = q(H('.wy-stage-svg'));
    if (!stage || !box) return false;
    var sr = stage.getBoundingClientRect();
    var br = box.getBoundingClientRect();
    var sx = br.left + br.width / 2;
    var sy = br.top + br.height / 2;
    var tx = sr.left + canvasPt[0] / 100 * sr.width;
    var ty = sr.top + canvasPt[1] / 100 * sr.height;
    function pe(type, cx, cy) {
      var ev;
      try {
        ev = new PointerEvent(type, { bubbles: true, cancelable: true,
          pointerId: 1, clientX: cx, clientY: cy, pointerType: 'mouse' });
      } catch (e) {
        ev = new MouseEvent(type, { bubbles: true, cancelable: true,
          clientX: cx, clientY: cy });
      }
      box.dispatchEvent(ev);
    }
    pe('pointerdown', sx, sy);
    pe('pointermove', tx, ty);
    pe('pointerup', tx, ty);
    return true;
  }

  function run() {
    var App = window.App;
    var MAP = App.levels.map;
    var want = 0;
    MAP.zones.forEach(function (z) { want += (z.objects || []).length; });

    try {
      App.store.del('wangyi');

      log('=== 一、数据与字形拆分 ===');
      log('底图=' + (MAP.bgImage || '(无)') + '　viewBox=' + MAP.viewBox);
      log('实物点=' + want + ' 个（' + MAP.zones.length + ' 个分区）');
      var totalPieces = 0, onePiece = [];
      Object.keys(App.glyphs.parts).forEach(function (c) {
        var n = App.glyphStrokeCount(c);
        totalPieces += n;
        if (n <= 1) onePiece.push(c);
      });
      log('字形可拆部件总数=' + totalPieces + '（61 个字）');
      log('只有 1 笔的字=' + (onePiece.join('、') || '无') + '（这些字的构字没有挑战）');

      log('');
      log('=== 二、地图初始状态：应该是灰的 ===');
      mountFresh();
      log('底层灰度图 wy-bg-dim=' + flag(!!q(H('.wy-bg-dim'))));
      log('上层彩色图 wy-bg-lit=' + flag(!!q(H('.wy-bg-lit'))));
      var lit = q(H('.wy-bg-lit'));
      log('上层挂了 mask=' + flag(!!(lit && lit.getAttribute('mask'))));
      var maskId = lit ? String(lit.getAttribute('mask')).replace(/^url\(#/, '').replace(/\)$/, '') : '';
      var maskEl = maskId ? document.getElementById(maskId) : null;
      log('mask 元素存在=' + flag(!!maskEl) +
          '　mask 里的白圆=' + (maskEl ? maskEl.querySelectorAll('circle').length : -1) +
          '（初始应为 0）');
      log('灰度滤镜=' + (q(H('.wy-bg-dim')) ? window.getComputedStyle(q(H('.wy-bg-dim'))).filter : '-'));
      log('热区数=' + spots().length + '（应 ' + want + '）');
      log('初始进度=' + txt(q(H('.wy-learnnum'))));

      log('');
      log('=== 三、点实物 → 进构字界面 ===');
      var ch = '鼎';
      var sp = spotByChar(ch);
      tap(sp);
      log('点了「' + ch + '」→ 构字界面=' + flag(!!q(H('.wy-stage-svg'))));
      log('上：甲骨文原字 wy-ref-glyph=' + flag(!!q(H('svg.wy-ref-glyph'))) +
          '　标签=「' + txt(q(H('.wy-ref-label'))) + '」');
      log('标题=「' + txt(q(H('.wy-title'))) + '」　' + txt(q(H('.wy-cell-rank'))));
      log('中：组装区=是　淡淡原字提示 wy-guide=' + flag(!!q(H('.wy-guide path'))));
      log('下：部件池=' + qa(H('.wy-tray-items .wy-piece')).length + ' 块（鼎应拆成 11 笔）');

      log('');
      log('=== 四、拖拽构字（模拟真实指针事件）===');
      var strokes = App.glyphStrokes(ch);
      var n = strokes.length;
      /* 先故意拖错一处，验证会拒绝 */
      var pieces0 = qa(H('.wy-tray-items .wy-piece'));
      dragTo(pieces0[0], [4, 96]);   /* 拖到角落，肯定不对 */
      log('故意拖到角落 → 判定=' + txt(q(H('.wy-verdict, .verdict'))));
      log('已摆数=' + qa(H('.wy-placed .wy-stroke')).length + '（应仍为 0）');

      /* 再逐笔拖到正确位置 */
      var fail = 0;
      for (var k = 0; k < n; k++) {
        var box = null;
        var cand = qa(H('.wy-tray-items .wy-piece'));
        for (var j = 0; j < cand.length; j++) {
          if (cand[j].getAttribute('data-i') === String(k)) { box = cand[j]; break; }
        }
        if (!box) { log('  ✗ 找不到第 ' + (k + 1) + ' 笔的部件'); fail++; continue; }
        var c = strokes[k].c;
        dragTo(box, [(c[0] + c[2]) / 2, (c[1] + c[3]) / 2]);
        var placedNow = qa(H('.wy-placed .wy-stroke')).length;
        if (placedNow !== k + 1) { log('  ✗ 第 ' + (k + 1) + ' 笔未就位（已摆 ' + placedNow + '）'); fail++; }
      }
      log('逐笔拖入：失败 ' + fail + ' / ' + n + (fail ? ' ✗' : ' ✓'));
      log('组装区笔画数=' + qa(H('.wy-placed .wy-stroke')).length + '（应 ' + n + '）');
      log('部件池剩余=' + qa(H('.wy-tray-items .wy-piece')).length + '（应 0）');
      log('判定=' + txt(q(H('.wy-verdict, .verdict'))));

      log('');
      log('=== 五、拼成 → 看释义 ===');
      var nx = btnByText(/^看看释义/);
      if (nx) tap(nx);
      log('卡片大字=' + txt(q(H('.wy-card-char'))) +
          '　大图=' + flag(!!q(H('.wy-card-form svg'))) +
          '　释义=' + txt(q(H('.wy-card-mean'))));
      log('存储=' + JSON.stringify(App.store.get('wangyi', null)));

      log('');
      log('=== 六、回地图：那一块应该亮了 ===');
      tap(btnByText(/回到地图/));
      log('在地图=' + flag(!!q(H('.wy-omap'))));
      var lit2 = q(H('.wy-bg-lit'));
      var mid2 = lit2 ? String(lit2.getAttribute('mask')).replace(/^url\(#/, '').replace(/\)$/, '') : '';
      var m2 = mid2 ? document.getElementById(mid2) : null;
      log('mask 里的白圆=' + (m2 ? m2.querySelectorAll('circle').length : -1) + '（应为 1）');
      if (m2 && m2.querySelector('circle')) {
        var cc = m2.querySelector('circle');
        log('  亮区圆心=(' + cc.getAttribute('cx') + ',' + cc.getAttribute('cy') +
            ') 半径=' + cc.getAttribute('r'));
        var o0 = null;
        MAP.zones.forEach(function (z) {
          (z.objects || []).forEach(function (o) { if (o.char === ch) o0 = o; });
        });
        log('  「' + ch + '」热区=(' + o0.x + ',' + o0.y + ' r' + o0.r + ')' +
            '　圆心对齐=' + flag(String(o0.x) === cc.getAttribute('cx')));
      }
      log('进度=' + txt(q(H('.wy-learnnum'))));
      log('已认标记 wy-spot.seen=' + qa(H('.wy-spot.seen')).length);

      log('');
      log('=== 七、再拼一个（水，看笔画少的字）===');
      tap(spotByChar('水'));
      var ns = App.glyphStrokeCount('水');
      log('「水」' + ns + ' 笔　部件池=' + qa(H('.wy-tray-items .wy-piece')).length);
      var s2 = App.glyphStrokes('水');
      var f2 = 0;
      for (var k2 = 0; k2 < ns; k2++) {
        var bx = null;
        var cd = qa(H('.wy-tray-items .wy-piece'));
        for (var j2 = 0; j2 < cd.length; j2++) {
          if (cd[j2].getAttribute('data-i') === String(k2)) { bx = cd[j2]; break; }
        }
        if (!bx) { f2++; continue; }
        var c2 = s2[k2].c;
        dragTo(bx, [(c2[0] + c2[2]) / 2, (c2[1] + c2[3]) / 2]);
      }
      log('拖入失败=' + f2 + '　组装区=' + qa(H('.wy-placed .wy-stroke')).length + '/' + ns);
      log('判定=' + txt(q(H('.wy-verdict, .verdict'))));
      tap(btnByText(/^看看释义/));
      tap(btnByText(/回到地图/));
      var m3 = q('.wy-bg-lit');
      var mid3 = m3 ? String(m3.getAttribute('mask')).replace(/^url\(#/, '').replace(/\)$/, '') : '';
      log('回地图后 mask 白圆=' + (document.getElementById(mid3) ?
        document.getElementById(mid3).querySelectorAll('circle').length : -1) + '（应为 2）');
      log('进度=' + txt(q(H('.wy-learnnum'))));

      log('');
      log('=== 八、重置 → 整幅画重新变灰 ===');
      log('重置按钮在=' + flag(!!btnByText(/重置点亮记录/)));
      App.store.del('wangyi');
      mountFresh();
      var m4 = q('.wy-bg-lit');
      var mid4 = m4 ? String(m4.getAttribute('mask')).replace(/^url\(#/, '').replace(/\)$/, '') : '';
      log('清空后 mask 白圆=' + (document.getElementById(mid4) ?
        document.getElementById(mid4).querySelectorAll('circle').length : -1) + '（应为 0）');
      log('进度=' + txt(q(H('.wy-learnnum'))));

    } catch (e) {
      log('!! 异常: ' + (e && e.message ? e.message : e));
      if (e && e.stack) { String(e.stack).split('\n').slice(0, 4).forEach(function (s) { log('   ' + s); }); }
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
