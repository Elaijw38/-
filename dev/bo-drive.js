/* 字趣 · 构件讨伐（线性关卡 + 横版对战）浏览器内验证 —— 开发自查，不参与部署
   由 dev/_run_bo.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   验两屏与一条规则：
     选关（.bo-track）21 关线性推进，未通关的锁住
     作战（.bd-field）横版：左「项目形象」预留位 + 右 BOSS
     规则：甲骨形上不直接印现代字，默认 opacity:0，hover/聚焦/按住才浮出

   硬约束（都踩过）：SVG 无 .click()，要派发事件；每次 render 会重建 DOM，
   动作前必须重新查询节点；全程同步，不用 setTimeout 排队。
*/
(function () {
  'use strict';
  var L = [], errs = [];
  window.addEventListener('error', function (e) { errs.push('ERROR: ' + e.message); });
  function log(s) { L.push(String(s)); }
  function q(s) { return document.querySelector(s); }
  function qa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function txt(e) { return e ? String(e.textContent).trim() : ''; }
  function flag(b) { return b ? '是' : '否'; }
  var HOST_ID = 'boProbeHost';
  function H(s) { return '#' + HOST_ID + ' ' + s; }
  function opa(e) { return e ? getComputedStyle(e).opacity : '?'; }

  function tap(el) {
    if (!el) { return false; }
    if (typeof el.click === 'function') { el.click(); return true; }
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return true;
  }
  function btnByText(re) {
    var l = qa(H('button'));
    for (var i = 0; i < l.length; i++) { if (re.test(txt(l[i]))) { return l[i]; } }
    return null;
  }
  function mountFresh() {
    var App = window.App;
    var old = document.getElementById(HOST_ID);
    if (old && old.parentNode) { old.parentNode.removeChild(old); }
    var host = document.createElement('div');
    host.id = HOST_ID;
    document.body.appendChild(host);
    var m = App.modes.get('boss-raid');
    m.mount(host, App.modes.buildContext(m));
  }
  function hit(el) {
    if (!el) { return false; }
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return true;
  }
  function nodes() { return qa(H('.bo-node')); }
  function openNodes() {
    return nodes().filter(function (n) { return n.className.indexOf('locked') < 0; });
  }
  function parts() { return qa(H('.bo-part')); }
  function cuts() { return qa(H('.bo-cut')); }
  function hp() { return txt(q(H('.bd-hpnum'))); }
  function phaseOn() {
    /* 整词匹配：className.indexOf('on') 会命中 'done' 里的 "on"（本驱动栽过） */
    var l = qa(H('.bd-phase'));
    for (var i = 0; i < l.length; i++) {
      if ((' ' + l[i].className + ' ').indexOf(' on ') >= 0) { return i + 1; }
    }
    return 0;
  }
  function clearLevel() {
    var g = 0;
    while (parts().length && g++ < 40) { hit(parts()[0]); }
    tap(btnByText(/改用笔画攻击/));
    var g2 = 0;
    while (cuts().length && g2++ < 40) { hit(cuts()[0]); }
    return g + ' 拆 / ' + g2 + ' 斩';
  }

  function run() {
    var App = window.App;
    try {
      App.store.del('bossraid');

      log('=== 一、玩法注册与关卡表 ===');
      var ms = App.modes.playable().map(function (m) { return m.id; });
      log('  已注册玩法: ' + ms.join('、'));
      log('  boss-raid 在: ' + flag(ms.indexOf('boss-raid') >= 0));
      var B = App.levels.boss;
      var total = B.tiers.reduce(function (n, t) { return n + t.list.length; }, 0);
      log('  关卡总数: ' + total + '（一阶 6 + 二阶 6 + 终极 9）');
      log('  玩法卡标签: ' + (App.modes.get('boss-raid').tags || []).join(' / '));

      log('');
      log('=== 二、线性关卡路径 ===');
      mountFresh();
      log('  路径节点: ' + nodes().length + '（应 ' + total + '）');
      log('  连接线: ' + qa(H('.bo-link')).length + '（应 ' + (total - 1) + '）');
      log('  已解锁: ' + openNodes().length + '（初始应 1）');
      log('  已锁定: ' + (nodes().length - openNodes().length) + '（应 ' + (total - 1) + '）');
      log('  高亮「该打这一关」: ' + qa(H('.bo-node.next')).length + '（应 1）');
      log('  总进度文案: ' + txt(q(H('.bo-progtext'))));

      log('');
      log('=== 三、现代字默认不显示（甲骨形上不印现代字）===');
      var nm = q(H('.bo-node-name'));
      log('  节点上的现代字: 「' + txt(nm) + '」　computed opacity=' + opa(nm) + '（应 0）');
      log('  第 1 关副标题: 「' + txt(q(H('.bo-node-meta'))) + '」（应是"构件 N 块"，不是"水＋止"）');

      log('');
      log('=== 四、第 1 关「涉」：横版作战 ===');
      tap(openNodes()[0]);
      log('  战场存在: ' + flag(!!q(H('.bd-field'))));
      var slots = qa(H('.bd-hero-slot'));
      log('  左侧「项目形象」预留位: ' + slots.length + ' 个　文案=「' + txt(slots[0]) + '」');
      log('  右侧 BOSS 区: ' + flag(!!q(H('.bd-boss'))));
      log('  BOSS 显示名默认: 「' + txt(q(H('.bd-ask'))) + '」（应为「？」）');
      var bn = q(H('.bd-boss .bo-spoiler-a'));
      log('  BOSS 真名 opacity=' + opa(bn) + '（应 0）　真名=「' + txt(bn) + '」');
      log('  远景装饰: ' + flag(!!q(H('.bd-scene'))) + '　地面: ' + flag(!!q(H('.bd-ground'))));
      log('  关卡号: ' + txt(q(H('.bd-lv'))) + '　档位: ' + txt(q(H('.bd-tier'))));
      log('  阶段: ' + phaseOn() + '（应 1）　血量: ' + hp());
      log('  可拆部件: ' + parts().length + '（涉＝水＋止，应 2）');
      log('  开战战报: 「' + txt(qa(H('.bd-log'))[0]) + '」（不应出现字名）');

      hit(parts()[0]);
      log('  拆一个 → 血量 ' + hp() + '　残影 ' + qa(H('.bo-gone')).length);
      log('  战报: ' + txt(qa(H('.bd-log'))[0]));
      hit(parts()[0]);
      log('  拆完两个 → 阶段 ' + phaseOn() + '（应 2）　血量 ' + hp());
            log('  阶段提示: ' + txt(q(H('.bd-tip'))));

      log('');
      log('=== 五、阶段二失效 → 阶段三斩笔画 → 通关 ===');
      var before = hp();
      var anyPart = parts()[0];
      log('  阶段二还能点部件: ' + flag(!!anyPart));
      if (anyPart) { hit(anyPart); }
      log('  点后血量: ' + before + ' → ' + hp() + '（应不变）');
      log('  出现「改用笔画攻击」: ' + flag(!!btnByText(/改用笔画攻击/)));
      tap(btnByText(/改用笔画攻击/));
      log('  阶段: ' + phaseOn() + '（应 3）　可斩: ' + cuts().length + ' 段');
      var g = 0;
      while (cuts().length && g++ < 40) { hit(cuts()[0]); }
            log('  通关页: ' + flag(!!q(H('.bd-win'))) + '　' + txt(q(H('.bd-wintitle'))));

      log('');
      log('=== 六、通关后线性推进 ===');
      tap(btnByText(/回到关卡/));
      log('  已解锁: ' + openNodes().length + '（应 2）');
      log('  第 1 关标记已通关: ' + flag(nodes()[0].className.indexOf('done') >= 0));
      log('  第 1 关现代字常显 opacity=' + opa(qa(H('.bo-node-name'))[0]) + '（应 1，已揭晓过）');
      log('  总进度: ' + txt(q(H('.bo-progtext'))));
      log('  连接线已点亮: ' + qa(H('.bo-link.done')).length + '（应 1）');

      log('');
      log('=== 七、最后一关（17 段繁复字）===');
      /* 解锁全部按钮会弹 confirm；无头下 confirm 返回 false，
         这里直接写存储再重挂载，等价于确认后的状态 */
      var p = { cleared: [] };
      for (var k = 0; k < total - 1; k++) { p.cleared.push(k); }
      App.store.set('bossraid', p);
      mountFresh();
      log('  已解锁: ' + openNodes().length + '（应 ' + total + '）');
      log('  「解锁全部」按钮在: ' + flag(!!btnByText(/解锁全部/)));
      tap(nodes()[total - 1]);
            log('  进入 ' + txt(q(H('.bd-lv'))) + '　' + txt(q(H('.bd-tier'))));
      log('  副标题: 「' + txt(q(H('.bd-boss .bd-side-role'))) + '」（应是笔画数，不是释义）');
      log('  可拆笔画: ' + parts().length + '（应 17）');
      var r = clearLevel();
            log('  ' + r + '　通关: ' + flag(!!q(H('.bd-win'))) + '　' + txt(q(H('.bd-wintitle'))));
      log('  含「繁笔破防」注释: ' + flag(!!q(H('.bd-winnote'))));

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
