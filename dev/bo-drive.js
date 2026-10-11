/* 字趣 · 构件讨伐（骨片选关 + 横版作战 + 自己挑构件）浏览器内验证
   由 dev/_run_bo.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   验四件事：
     1 选关沿甲骨片轮廓围成一圈（.bo-bone / .bo-bead）
     2 横版战场：左「项目形象」预留位 + 右 BOSS
     3 甲骨形上不印现代字（默认 opacity:0，悬停/聚焦/按住才浮出）
     4 阶段一必须**自己从构件池挑构件**：池子 37 个、挑错记误选、
       直接点身上那块不再生效；零误选通关记「完美通关」

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
  function beads() { return qa(H('.bo-bead')); }
  function openBeads() {
    return beads().filter(function (n) { return n.className.indexOf('locked') < 0; });
  }
  function chips() { return qa(H('.bd-chip')); }
  function chipByName(c) {
    var l = chips();
    for (var i = 0; i < l.length; i++) {
      var n = l[i].querySelector('.bd-chipname');
      if (txt(n) === c) { return l[i]; }
    }
    return null;
  }
  function parts() { return qa(H('.bo-part')); }
  function cuts() { return qa(H('.bo-cut')); }
  function hp() { return txt(q(H('.bd-hpnum'))); }
  function hpNum() { var m = /(\d+)%/.exec(hp()); return m ? parseInt(m[1], 10) : -1; }
  function logs() { return qa(H('.bd-log')).map(txt); }
  function hasLog(re) {
    return logs().some(function (s) { return re.test(s); });
  }
  function phaseOn() {
    /* 整词匹配：className.indexOf('on') 会命中 'done' 里的 "on"（本驱动栽过） */
    var l = qa(H('.bd-phase'));
    for (var i = 0; i < l.length; i++) {
      if ((' ' + l[i].className + ' ').indexOf(' on ') >= 0) { return i + 1; }
    }
    return 0;
  }
  function cutAll() {
    var g = 0;
    while (cuts().length && g++ < 40) { hit(cuts()[0]); }
    return g;
  }

  function run() {
    var App = window.App;
    try {
      App.store.del('bossraid');

      log('=== 一、注册与关卡表 ===');
      var ms = App.modes.playable().map(function (m) { return m.id; });
      log('  已注册玩法: ' + ms.join('、'));
      var B = App.levels.boss;
      var total = B.tiers.reduce(function (n, t) { return n + t.list.length; }, 0);
      log('  关卡总数: ' + total + '（一阶 6 + 二阶 6 + 终极 9）');
      log('  构件池: ' + (B.palette || []).length + ' 个（应 37，含干扰项）');
      log('  玩法卡标签: ' + (App.modes.get('boss-raid').tags || []).join(' / '));

      log('');
      log('=== 二、骨片形状的选关 ===');
      mountFresh();
      log('  骨片底板: ' + flag(!!q(H('.bo-boneplate'))));
      log('  轮廓/路径层: ' + flag(!!q(H('.bo-boneline'))));
      log('  轮廓多边形顶点数: ' + (function () {
        var p = q(H('.bo-boneedge'));
        return p ? p.getAttribute('points').split(' ').length : -1;
      })() + '（应 12）');
      log('  关卡珠子: ' + beads().length + '（应 ' + total + '）');
      /* 珠子是不是真的"围成一圈"：位置应同时覆盖上下左右四个方向 */
      var pos = beads().map(function (b) { return parseFloat(b.style.left); });
      var top = beads().map(function (b) { return parseFloat(b.style.top); });
      log('  横向分布: ' + Math.min.apply(null, pos).toFixed(1) + '% ~ '
        + Math.max.apply(null, pos).toFixed(1) + '%');
      log('  纵向分布: ' + Math.min.apply(null, top).toFixed(1) + '% ~ '
        + Math.max.apply(null, top).toFixed(1) + '%（围成圈就应横竖都铺开）');
      log('  已解锁: ' + openBeads().length + '（初始应 1）');
      log('  已锁定: ' + (beads().length - openBeads().length) + '（应 ' + (total - 1) + '）');
      log('  高亮「该打这一关」: ' + qa(H('.bo-bead.next')).length + '（应 1）');
      log('  骨片正中进度: 「' + txt(q(H('.bo-corenum'))) + '」　'
        + txt(q(H('.bo-corenote'))));

      log('');
      log('=== 三、现代字默认不显示 ===');
      var nm = q(H('.bo-beadname'));
      log('  珠子上的现代字: 「' + txt(nm) + '」　computed opacity=' + opa(nm) + '（应 0）');
      log('  珠子 title（原生提示里才有说明）: 「' + beads()[0].getAttribute('title') + '」');

      log('');
      log('=== 四、第 1 关「涉」：横版 + 自己挑构件 ===');
      tap(openBeads()[0]);
      log('  战场: ' + flag(!!q(H('.bd-field'))) + '　左预留位: '
        + flag(!!q(H('.bd-hero-slot'))) + '　右 BOSS: ' + flag(!!q(H('.bd-boss'))));
      log('  左侧预留位文案: 「' + txt(q(H('.bd-hero-slot'))) + '」');
      log('  BOSS 名: 「' + txt(q(H('.bd-ask'))) + '」　真名 opacity='
        + opa(q(H('.bd-boss .bo-spoiler-a'))) + '（应 0）');
      log('  阶段: ' + phaseOn() + '（应 1）　血量: ' + hp());
      log('  构件池: ' + flag(!!q(H('.bd-pool'))) + '　牌子数 ' + chips().length
        + '（应 37）');
      log('  池子说明: 「' + txt(q(H('.bd-pool-note'))) + '」');
      var cn = q(H('.bd-chipname'));
      log('  构件名默认很淡: 「' + txt(cn) + '」opacity=' + opa(cn) + '（应 <1，浅浅的）');

      log('');
      log('--- 身上那块不能直接点（点了等于报答案）---');
      log('  战场带 pool-only: ' + flag(!!q(H('.bd-field.pool-only'))));
      log('  身上可拆部件数: ' + parts().length + '（仍是 2，只是不可点）');
      log('  可点热区 .bo-hit 的 pointer-events: '
        + (q(H('.bo-part .bo-hit path')) ? getComputedStyle(q(H('.bo-part .bo-hit'))).pointerEvents : '无'));
      var beforeClick = hpNum();
      hit(parts()[0]);
      log('  直接点身上一块 → 血量 ' + beforeClick + '% → ' + hpNum() + '%（应不变）');

      log('');
      log('--- 挑错：记一次误选，不掉血 ---');
      var wrong = chips().filter(function (c) {
        var n = txt(c.querySelector('.bd-chipname'));
        return n !== '水' && n !== '止';
      })[0];
      log('  挑一个不在它身上的: 「' + txt(wrong.querySelector('.bd-chipname')) + '」');
      hit(wrong);
      log('  血量: ' + hpNum() + '%（应仍 100）');
      log('  出现"砸空了"战报: ' + flag(hasLog(/砸空了/)));
      log('  池子说明里的误选计数: 「' + txt(q(H('.bd-pool-note'))) + '」');

      log('');
      log('--- 挑对：拆下来、掉血、报出构件能力 ---');
      hit(chipByName('水'));
      log('  挑「水」→ 血量 ' + hpNum() + '%（应 75）');
      log('  战报: ' + logs()[0]);
      hit(chipByName('止'));
      log('  挑「止」→ 血量 ' + hpNum() + '%　阶段 ' + phaseOn() + '（应 2）');
      log('  阶段提示: 「' + txt(q(H('.bd-tip'))) + '」');
      log('  池子已失效: 「' + txt(q(H('.bd-pool-note'))) + '」　dead 牌子 '
        + qa(H('.bd-chip.dead')).length + '（应 37）');

      log('');
      log('=== 五、阶段三斩笔画 → 通关 ===');
      tap(btnByText(/改用笔画攻击/));
      log('  阶段: ' + phaseOn() + '（应 3）　可斩: ' + cuts().length + ' 段');
      var g = cutAll();
      log('  斩击轮次: ' + g + '　通关页: ' + flag(!!q(H('.bd-win'))));
      log('  通关标题: ' + txt(q(H('.bd-wintitle'))));
      log('  误选成绩单: 「' + txt(q(H('.bd-winnote'))) + '」');
      log('  记为本关完美通关（因有误选，应是否）: '
        + flag(!!q(H('.bd-winnote.perfect'))));

      log('');
      log('=== 六、零误选通关 → 完美通关 ===');
      tap(btnByText(/再打一次/));
      log('  回到第 1 关，阶段 ' + phaseOn() + '　血量 ' + hpNum() + '%');
      hit(chipByName('水'));
      hit(chipByName('止'));
      tap(btnByText(/改用笔画攻击/));
      cutAll();
      log('  通关: ' + flag(!!q(H('.bd-win'))) + '　完美标记: '
        + flag(!!q(H('.bd-winnote.perfect'))));
      log('  成绩单: 「' + txt(q(H('.bd-winnote'))) + '」');

      log('');
      log('=== 七、通关后推进 + 骨片路径 ===');
      tap(btnByText(/回到关卡/));
      log('  已解锁: ' + openBeads().length + '（应 2）');
      log('  第 1 关已通关: ' + flag(beads()[0].className.indexOf('done') >= 0));
      log('  第 1 关完美: ' + flag(beads()[0].className.indexOf('perfect') >= 0));
      log('  第 1 关现代字常显 opacity=' + opa(qa(H('.bo-beadname'))[0]) + '（应 1）');
      log('  已通关路径段: ' + flag(!!q(H('.bo-bonedone'))));
      log('  骨片正中: 「' + txt(q(H('.bo-corenum'))) + '」');
      log('  进度文案（含完美计数）: 「' + txt(q(H('.bo-progtext'))) + '」');

      log('');
      log('=== 八、复杂档（末关 17 段）：直接点 BOSS 拆笔画 ===');
      var p2 = { cleared: [], perfect: [] };
      for (var k = 0; k < total - 1; k++) { p2.cleared.push(k); }
      App.store.set('bossraid', p2);
      mountFresh();
      log('  已解锁: ' + openBeads().length + '（应 ' + total + '）');
      tap(beads()[total - 1]);
            log('  进入 ' + txt(q(H('.bd-lv'))) + '　' + txt(q(H('.bd-tier'))));
      log('  构件池: ' + flag(!!q(H('.bd-pool'))) + '（复杂档没有可挑的构件，应"否"）');
      log('  身上可拆笔画: ' + parts().length + '（应 17，可直接点）');
      var g2 = 0;
      while (parts().length && g2++ < 40) { hit(parts()[0]); }
      log('  拆 17 段用了 ' + g2 + ' 轮　阶段 ' + phaseOn() + '（应 2）');
      tap(btnByText(/改用笔画攻击/));
      var g3 = cutAll();
      log('  斩 ' + g3 + ' 轮　通关: ' + flag(!!q(H('.bd-win'))) + '　'
        + txt(q(H('.bd-wintitle'))));

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
