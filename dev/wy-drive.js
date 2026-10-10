/* 字趣 · 王邑实物地图（热区版）的浏览器内验证 —— 开发自查用，不参与部署
   由 dev/_run_wy.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   验的是「点画上的实物 → 学那个甲骨文」这条主线，且**画上不出现任何标记**。

   三条硬约束（都是踩过的坑）：
     1) SVG 元素没有 HTMLElement.click()，必须派发事件（tap）。
     2) 每次渲染都会 clearNode 重建 DOM，每个动作前必须【重新查询】节点。
     3) 全程【同步】，不用 setTimeout 排队：Edge 的 --virtual-time-budget
        会把虚拟时间快进，与 setTimeout 链相遇会互相触发、进程不退出。
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
  function flag(b) { return b ? '是' : '否'; }
  function cs(e, prop) { return e ? window.getComputedStyle(e).getPropertyValue(prop) : ''; }

  var HOST_ID = 'wyProbeHost';
  function H(s) { return '#' + HOST_ID + ' ' + s; }

  function tap(el) {
    if (!el) { return false; }
    if (typeof el.click === 'function') { el.click(); return true; }
    var ev;
    try {
      ev = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
    } catch (e) {
      ev = document.createEvent('MouseEvents');
      ev.initEvent('click', true, true);
    }
    el.dispatchEvent(ev);
    return true;
  }

  function spots() { return qa(H('.wy-spot')); }
  function spotByChar(ch) {
    var list = spots();
    for (var i = 0; i < list.length; i++) {
      var al = list[i].getAttribute('aria-label') || '';
      if (al.indexOf(ch + '，') === 0) { return list[i]; }
    }
    return null;
  }
  function btnByText(re) {
    var list = qa(H('button'));
    for (var i = 0; i < list.length; i++) {
      if (re.test(txt(list[i]))) { return list[i]; }
    }
    return null;
  }
  function mountFresh() {
    var App = window.App;
    var old = document.getElementById(HOST_ID);
    if (old && old.parentNode) { old.parentNode.removeChild(old); }
    var host = document.createElement('div');
    host.id = HOST_ID;
    document.body.appendChild(host);
    var mode = App.modes.get('wangyi-map');
    mode.mount(host, App.modes.buildContext(mode));
  }

  function run() {
    var App = window.App;
    var MAP = App.levels.map;
    var want = 0;
    MAP.zones.forEach(function (z) { want += (z.objects || []).length; });

    try {
      App.store.del('wangyi');

      log('=== 一、底图与数据 ===');
      log('底图配置=' + (MAP.bgImage || '(无)'));
      log('viewBox=' + MAP.viewBox);
      log('实物点应为 ' + want + ' 个（' + MAP.zones.length + ' 个分区：' +
        MAP.zones.map(function (z) { return z.name; }).join('、') + '）');

      log('');
      log('=== 二、画上是否真的没有标记 ===');
      mountFresh();
      var img = q(H('.wy-omap image'));
      log('图卷 image 元素=' + flag(!!img) + '  href=' + (img ? img.getAttribute('href') : '-'));
      log('热区数=' + spots().length + '（应 ' + want + '）' +
        (spots().length === want ? ' ✓' : ' ✗'));
      /* 注意：opacity 不会以「计算值」继承，父组不透明度为 0 时
         子元素的 own opacity 仍是 1。所以要判「看得见」必须看承载组本身，
         不能逐个读内部 text 的 opacity（早先这么写过，误报 61）。 */
      var visPop = qa(H('.wy-omap .wy-pop')).filter(function (g) {
        return window.getComputedStyle(g).opacity !== '0';
      }).length;
      log('可见的悬停字形牌=' + visPop + '（应为 0——字形只在悬停时浮出）');
      log('热区轮廓默认不透明度=' + cs(q(H('.wy-spot .wy-ring')), 'opacity') + '（应为 0）');
      log('悬停字形牌默认不透明度=' + cs(q(H('.wy-spot .wy-pop')), 'opacity') + '（应为 0）');
      log('初始进度=' + txt(q(H('.wy-learnnum'))));

      log('');
      log('=== 三、逐个点热区（点它 → 学它）===');
      var failed = 0;
      ['山', '水', '木', '牛', '鼎', '门', '弓', '贝', '日', '目'].forEach(function (ch) {
        var g = spotByChar(ch);
        if (!g) { log('  ✗ 找不到「' + ch + '」的热区'); failed++; return; }
        tap(g);
        var shown = txt(q(H('.wy-card-char')));
        var mean = txt(q(H('.wy-card-mean')));
        var zone = txt(q(H('.wy-card-zone')));
        var big = qa(H('.wy-card-form svg')).length;
        var data = null;
        MAP.zones.forEach(function (z) {
          (z.objects || []).forEach(function (o) { if (o.char === ch) { data = o; } });
        });
        var ok = (shown === ch) && !!data && (mean === data.meaning) && big === 1;
        if (!ok) { failed++; }
        log('  ' + (ok ? '✓' : '✗') + ' 「' + ch + '」大字=' + shown +
          ' 大图=' + big + ' 分区=' + zone + ' 释义=' + mean);
        tap(btnByText(/回到地图/));
        if (!q(H('.wy-omap'))) { log('      !! 回地图失败'); failed++; }
      });
      log('失败项=' + failed + (failed ? ' ✗' : ' ✓'));

      log('');
      log('=== 四、学习进度 ===');
      log('存储=' + JSON.stringify(App.store.get('wangyi', null)));
      log('已认绿点=' + qa(H('.wy-seen-dot')).length + '（应 10）');
      log('进度显示=' + txt(q(H('.wy-learnnum'))) +
        '　进度条=' + (q(H('.wy-meter-fill')) ? q(H('.wy-meter-fill')).style.width : '(无)'));

      log('');
      log('=== 五、「显示可点处」开关（触屏的可发现性手段）===');
      var tb = btnByText(/显示可点处/);
      log('按钮文案=「' + txt(tb) + '」');
      tap(tb);
      log('打开后轮廓不透明度=' + cs(q(H('.wy-spot .wy-ring')), 'opacity') + '（应 > 0）');
      log('包装类含 show-hots=' + flag(!!q(H('.wy-map.show-hots'))));
      tap(btnByText(/隐藏可点处/));
      log('再关闭后不透明度=' + cs(q(H('.wy-spot .wy-ring')), 'opacity') + '（应回到 0）');

      log('');
      log('=== 六、接着认 / 上一个下一个 ===');
      tap(spotByChar('鼎'));
      var minis = qa(H('.wy-more .wy-mini'));
      var names = minis.map(function (b) { return txt(b.querySelector('.wy-mini-name')); });
      log('接着认=' + minis.length + ' 个：' + names.join('、'));
      if (minis.length) {
        var t0 = names[0];
        tap(minis[0]);
        log('点「' + t0 + '」→ 得「' + txt(q(H('.wy-card-char'))) + '」' +
          (txt(q(H('.wy-card-char'))) === t0 ? ' ✓' : ' ✗'));
      }
      var before = txt(q(H('.wy-card-char')));
      tap(btnByText(/下一个/));
      var mid = txt(q(H('.wy-card-char')));
      tap(btnByText(/上一个/));
      var back = txt(q(H('.wy-card-char')));
      log('「' + before + '」→ 下「' + mid + '」→ 上「' + back + '」' +
        ((mid !== before && back === before) ? ' ✓' : ' ✗'));

      log('');
      log('=== 七、键盘可用 ===');
      tap(btnByText(/回到地图/));
      var g2 = spotByChar('鹿');
      if (g2) {
        var kev = null;
        try { kev = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }); } catch (e) { kev = null; }
        if (kev) {
          g2.dispatchEvent(kev);
          var got = txt(q(H('.wy-card-char')));
          log('在「鹿」上按回车 → 得「' + got + '」' + (got === '鹿' ? ' ✓' : ' ✗'));
        } else { log('（本环境不支持构造键盘事件，跳过）'); }
      } else { log('✗ 找不到「鹿」'); }

      log('');
      log('=== 八、答题练习入口仍在 ===');
      tap(btnByText(/回到地图/));
      var qb = btnByText(/答题练习/);
      if (qb) {
        log('入口=「' + txt(qb) + '」');
        tap(qb);
        log('练习分组=' + qa(H('.wy-zb-name')).map(txt).join('、'));
        tap(btnByText(/回到地图/));
        log('已回地图=' + flag(!!q(H('.wy-omap'))));
      } else {
        log('✗ 入口缺失（地图上按钮：' + qa(H('button')).map(txt).join(' | ') + '）');
      }

      log('');
      log('=== 九、卸载后重挂载应回到地图 ===');
      tap(spotByChar('鱼'));
      var inDetail = !!q(H('.wy-card'));
      App.modes.get('wangyi-map').unmount(document.getElementById(HOST_ID));
      mountFresh();
      log('卸载前在详情=' + flag(inDetail) +
        '　重挂载后地图在=' + flag(!!q(H('.wy-omap'))) +
        '　详情残留=' + flag(!!q(H('.wy-card'))) +
        '　开关已复位=' + flag(!q(H('.wy-map.show-hots'))));

      log('');
      log('=== 十、重置 ===');
      log('重置按钮在=' + flag(!!btnByText(/重置学习记录/)));
      App.store.del('wangyi');
      mountFresh();
      log('清空后进度=' + txt(q(H('.wy-learnnum'))) +
        '　绿点=' + qa(H('.wy-seen-dot')).length);

      /* 留一张热区显形的地图供截图核对 */
      tap(btnByText(/显示可点处/));
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
