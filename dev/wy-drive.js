/* 字趣 · 王邑实物地图的浏览器内验证（开发自查用，不参与部署）
   由 dev/_run_wy.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   验的是「点地图上的实物 → 学那个甲骨文」这条主线。

   三条硬约束（都是踩过的坑）：
     1) SVG 元素没有 HTMLElement.click()，必须派发事件（tap）。
     2) 每次渲染都会 clearNode 重建 DOM，所以每个动作之前必须【重新查询】节点，
        不能把上一轮的引用留到下一轮——否则会"找不到"明明还在的实物。
     3) 全程【同步】执行，不用 setTimeout 排队。
        Edge 的 --virtual-time-budget 会把虚拟时间快进，
        与 setTimeout 链相遇会互相触发导致进程不退出（实测挂死 300 秒）。
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

  function objs() { return qa(H('.wy-obj')); }
  function objLabel(g) {
    var t = g ? g.querySelector('.wy-obj-label') : null;
    return t ? String(t.textContent).trim() : '';
  }
  function objByChar(ch) {
    var list = objs();
    for (var i = 0; i < list.length; i++) {
      if (objLabel(list[i]) === ch) { return list[i]; }
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

      log('=== 一、地图数据 ===');
      log('区块 ' + MAP.zones.length + ' 个：' +
        MAP.zones.map(function (z) { return z.name; }).join('、'));
      log('实物点应为 ' + want + ' 个');

      log('');
      log('=== 二、实物是否都画到图上 ===');
      mountFresh();
      var noGlyph = objs().filter(function (g) {
        return !g.querySelector('.wy-obj-form svg') && !g.querySelector('.wy-obj-form path');
      });
      var noLabel = objs().filter(function (g) { return !objLabel(g); });
      log('地图 SVG=' + flag(!!q(H('.wy-omap'))));
      log('实物节点=' + objs().length + '（应 ' + want + '）' +
        (objs().length === want ? ' ✓' : ' ✗'));
      log('无字形=' + noGlyph.length + (noGlyph.length ? '（' + noGlyph.map(objLabel).join('、') + '）' : ' ✓'));
      log('无今字标签=' + noLabel.length + (noLabel.length ? ' ✗' : ' ✓'));
      log('区块标题=' + qa(H('.wy-zone-title')).map(txt).join(' / '));
      log('背景实景元素=' + qa(H('.wy-backdrop > *')).length);
      log('初始进度=' + txt(q(H('.wy-learnnum'))));

      log('');
      log('=== 三、逐个点开实物（点它 → 学它）===');
      var failed = 0;
      ['山', '木', '牛', '鼎', '日', '水', '虎', '贝'].forEach(function (ch) {
        var g = objByChar(ch);
        if (!g) { log('  ✗ 地图上找不到「' + ch + '」'); failed++; return; }
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
          ' 大图=' + big + ' 归属=' + zone + ' 释义=' + mean);
        tap(btnByText(/回到地图/));
        if (!q(H('.wy-omap'))) { log('       !! 回地图失败'); failed++; }
      });
      log('失败项=' + failed + (failed ? ' ✗' : ' ✓'));

      log('');
      log('=== 四、学习进度是否记下 ===');
      log('存储=' + JSON.stringify(App.store.get('wangyi', null)));
      log('地图上的印记数=' + qa(H('.wy-obj.seen')).length + '（应 8）');
      log('进度显示=' + txt(q(H('.wy-learnnum'))) +
        '　进度条=' + (q(H('.wy-meter-fill')) ? q(H('.wy-meter-fill')).style.width : '(无)'));

      log('');
      log('=== 五、同区其它实物（顺着看下去）===');
      tap(objByChar('木'));
      var minis = qa(H('.wy-more .wy-mini'));
      var names = minis.map(function (b) { return txt(b.querySelector('.wy-mini-name')); });
      log('推荐 ' + minis.length + ' 个：' + names.slice(0, 9).join('、') +
        (names.length > 9 ? ' …' : ''));
      if (minis.length) {
        var target = names[0];
        tap(minis[0]);
        var shown2 = txt(q(H('.wy-card-char')));
        log('点第一个「' + target + '」→ 得「' + shown2 + '」' + (shown2 === target ? ' ✓' : ' ✗'));
      }

      log('');
      log('=== 六、上一个 / 下一个 ===');
      var before = txt(q(H('.wy-card-char')));
      tap(btnByText(/下一个/));
      var mid = txt(q(H('.wy-card-char')));
      tap(btnByText(/上一个/));
      var back = txt(q(H('.wy-card-char')));
      log('「' + before + '」→ 下「' + mid + '」→ 上「' + back + '」' +
        ((mid !== before && back === before) ? ' ✓' : ' ✗'));

      log('');
      log('=== 七、键盘也能用 ===');
      /* 先确保回到地图：上一步结束在详情页，不回去就找不到实物节点
         （踩过：把"回地图"写在后面的步骤里，前面失败就一路串味） */
      tap(btnByText(/回到地图/));
      log('起始在地图=' + flag(!!q(H('.wy-omap'))));
      var g2 = objByChar('鹿');
      if (g2) {
        var kev = null;
        try { kev = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }); } catch (e) { kev = null; }
        if (kev) {
          g2.dispatchEvent(kev);
          var got = txt(q(H('.wy-card-char')));
          log('在「鹿」上按回车 → 卡片大字=' + got + (got === '鹿' ? ' ✓' : ' ✗'));
        } else { log('（本环境不支持构造键盘事件，跳过）'); }
      } else { log('✗ 找不到「鹿」'); }

      log('');
      log('=== 八、答题练习入口仍在 ===');
      tap(btnByText(/回到地图/));
      var qb = btnByText(/答题练习/);
      if (qb) {
        log('入口文案=「' + txt(qb) + '」');
        tap(qb);
        var znames = qa(H('.wy-zb-name')).map(txt);
        log('练习分组=' + znames.join('、') + '　列表在=' + flag(!!q(H('.wy-zlist'))));
        tap(btnByText(/回到地图/));
        log('已回地图=' + flag(!!q(H('.wy-omap'))));
      } else {
        log('✗ 入口缺失（地图上按钮：' + qa(H('button')).map(txt).join(' | ') + '）');
      }

      log('');
      log('=== 九、卸载后重挂载应回到地图 ===');
      tap(objByChar('囗'));
      var inDetail = !!q(H('.wy-card'));
      var mode = App.modes.get('wangyi-map');
      mode.unmount(document.getElementById(HOST_ID));
      mountFresh();
      log('卸载前在详情=' + flag(inDetail) +
        '　重挂载后地图在=' + flag(!!q(H('.wy-omap'))) +
        '　详情残留=' + flag(!!q(H('.wy-card'))));

      log('');
      log('=== 十、重置学习记录 ===');
      /* 重置会弹 confirm，脚本环境默认返回 false，故只验按钮存在 */
      log('重置按钮在=' + flag(!!btnByText(/重置学习记录/)));
      App.store.del('wangyi');
      mountFresh();
      log('清空后进度=' + txt(q(H('.wy-learnnum'))) +
        '　印记=' + qa(H('.wy-obj.seen')).length);

      /* 留一张干净的地图供截图核对 */
      mountFresh();
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
