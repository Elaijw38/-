/* 字趣 · 构件讨伐（BOSS 战）的浏览器内验证 —— 开发自查，不参与部署
   由 dev/_run_bo.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   验三档 BOSS 与三阶段：
     一阶 合体：身体＝构件拼成，点构件拆下来 → 掉血 → 阶段二 → 阶段三斩笔画 → 通关
     二阶 独体：身上无构件，直接拆笔画
     终极 繁复：車 17 段，硬拆构件无效，必须走笔画终局

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

  function tap(el) {
    if (!el) return false;
    if (typeof el.click === 'function') { el.click(); return true; }
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return true;
  }
  function btnByText(re) {
    var l = qa(H('button'));
    for (var i = 0; i < l.length; i++) { if (re.test(txt(l[i]))) return l[i]; }
    return null;
  }
  function mountFresh() {
    var App = window.App;
    var old = document.getElementById(HOST_ID);
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var host = document.createElement('div');
    host.id = HOST_ID;
    document.body.appendChild(host);
    var m = App.modes.get('boss-raid');
    m.mount(host, App.modes.buildContext(m));
  }
  /* 派发点击到一个 SVG 子节点（用坐标命中的那层也行，这里按选择器取） */
  function hit(el) {
    if (!el) return false;
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return true;
  }
  function parts() { return qa(H('.bo-part')); }
  function cuts() { return qa(H('.bo-cut')); }
  function hp() { return txt(q(H('.bo-hpnum'))); }
  function phaseOn() {
    /* 注意：不能写 className.indexOf('on')——「done」里也含 "on"，
       会把已完成的阶段误判成当前阶段（本驱动就栽过这一次）。
       要按整词匹配，前后补空格。 */
    var l = qa(H('.bo-phase'));
    for (var i = 0; i < l.length; i++) {
      if ((' ' + l[i].className + ' ').indexOf(' on ') >= 0) { return i + 1; }
    }
    return 0;
  }
  function enterBoss(tierId, idx) {
    var cards = qa(H('.bo-grid .bo-card'));
    /* 按档位顺序累计索引 */
    var App = window.App, B = App.levels.boss;
    var off = 0;
    for (var i = 0; i < B.tiers.length; i++) {
      if (B.tiers[i].id === tierId) { break; }
      off += B.tiers[i].list.length;
    }
    tap(cards[off + idx]);
  }

  function run() {
    var App = window.App;
    try {
      log('=== 一、玩法是否注册 ===');
      var ms = App.modes.playable().map(function (m) { return m.id; });
      log('  已注册玩法: ' + ms.join('、'));
      log('  boss-raid 在: ' + flag(ms.indexOf('boss-raid') >= 0));
      var B = App.levels.boss;
      log('  BOSS 档位: ' + B.tiers.map(function (t) { return t.name + '(' + t.list.length + ')'; }).join('　'));
      log('  BOSS 总数: ' + B.tiers.reduce(function (n, t) { return n + t.list.length; }, 0));
      var miss = [];
      B.tiers.forEach(function (t) {
        t.list.forEach(function (b) {
          if (t.kind !== 'compound' && !App.hasGlyph(b.char)) { miss.push(b.char); }
        });
      });
      log('  缺字形的 BOSS: ' + (miss.length ? miss.join('、') + ' ✗' : '无 ✓'));

      log('');
      log('=== 二、选择页 ===');
      mountFresh();
      log('  档位区块: ' + qa(H('.bo-sect')).length + '（应 3）');
      log('  BOSS 卡片: ' + qa(H('.bo-card')).length + '（应 21）');
      log('  合体卡片（双构件合体图）: ' + qa(H('.bo-card.is-comp')).length + '（应 6）');

      log('');
      log('=== 三、一阶合体「涉」（水＋止）：拆构件 → 崩坏 → 斩笔画 ===');
      enterBoss('grunt', 0);
      log('  进入战斗: ' + flag(!!q(H('.bo-body'))));
      log('  标题: ' + txt(q(H('.bo-title'))));
      log('  阶段: ' + phaseOn() + '（应 1）　血量: ' + hp());
      log('  身体上可拆部件: ' + parts().length + '（涉＝水＋止，应 2）');
      var p0 = parts();
      log('  第一个部件标题: ' + (p0[0] ? txt(p0[0].querySelector('title')) : '-'));
      hit(p0[0]);
      log('  拆掉一个后 → 血量 ' + hp() + '　已拆残影 ' + qa(H('.bo-gone')).length);
      var logs1 = qa(H('.bo-log'));
      log('  战报条数: ' + logs1.length + '　最新: ' + txt(logs1[0]));
      hit(parts()[0]);
      log('  拆完两个 → 阶段 ' + phaseOn() + '（应 2）　血量 ' + hp());
      log('  阶段二提示: ' + txt(q(H('.bo-tip'))));

      log('');
      log('=== 四、阶段二：构件打法失效 ===');
      var before = hp();
      var anyPart = parts()[0];
      log('  阶段二还有可点部件: ' + flag(!!anyPart));
      if (anyPart) { hit(anyPart); }
      log('  点它之后血量: ' + before + ' → ' + hp() + '（应不变，构件失效）');
      var lg = qa(H('.bo-log'));
      log('  战报最新: ' + txt(lg[0]));
      log('  出现「改用笔画攻击」按钮: ' + flag(!!btnByText(/改用笔画攻击/)));

      log('');
      log('=== 五、阶段三：笔画终局 → 通关 ===');
      tap(btnByText(/改用笔画攻击/));
      log('  阶段: ' + phaseOn() + '（应 3）');
      var total = cuts().length;
      log('  可斩笔画: ' + total + '（涉：水 5 段 + 止 ? 段）');
      var guard = 0;
      while (cuts().length && guard++ < 60) { hit(cuts()[0]); }
      log('  斩击轮次: ' + guard);
      log('  通关页出现: ' + flag(!!q(H('.bo-win'))));
      log('  通关标题: ' + txt(q(H('.bo-wintitle'))));

      log('');
      log('=== 六、二阶独体「山」（1 段） ===');
      tap(btnByText(/换一尊/));
      log('  回到选择页: ' + flag(qa(H('.bo-card')).length > 0));
      enterBoss('solo', 0);
      log('  进入「' + txt(q(H('.bo-title'))) + '」　阶段 ' + phaseOn());
      log('  可拆部件: ' + parts().length + '（山＝1 段，应 1）');
      hit(parts()[0]);
      log('  拆掉后 → 阶段 ' + phaseOn() + '（应 2）');
      tap(btnByText(/改用笔画攻击/));
      log('  阶段三可斩: ' + cuts().length);
      var g2 = 0;
      while (cuts().length && g2++ < 30) { hit(cuts()[0]); }
      log('  通关: ' + flag(!!q(H('.bo-win'))) + '　' + txt(q(H('.bo-wintitle'))));

      log('');
      log('=== 七、终极「車」（17 段繁复字） ===');
      tap(btnByText(/换一尊/));
      enterBoss('elite', 7);   /* elite 列表第 8 个 = 車 */
      log('  进入「' + txt(q(H('.bo-title'))) + '」　' + txt(q(H('.bo-sub'))));
      log('  阶段一可拆笔画: ' + parts().length + '（車＝17 段，应 17）');
      var g3 = 0;
      while (parts().length && g3++ < 40) { hit(parts()[0]); }
      log('  拆完 17 段用了 ' + g3 + ' 轮　阶段 ' + phaseOn() + '（应 2）');
      tap(btnByText(/改用笔画攻击/));
      log('  阶段三可斩: ' + cuts().length + '（应 17）');
      var g4 = 0;
      while (cuts().length && g4++ < 40) { hit(cuts()[0]); }
      log('  通关: ' + flag(!!q(H('.bo-win'))) + '　' + txt(q(H('.bo-wintitle'))));
      log('  通关说明: ' + txt(q(H('.bo-windesc'))));
      log('  有繁复字注释: ' + flag(!!q(H('.bo-winnote'))));

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
