/* 演示模式 —— 给评委/老师在三分钟内看到"玩到后面的样子"。
 *
 * 为什么需要：全站的学习内容都锁在玩法后面（第二关 0/61、第三关 0/21、
 * 图鉴 0/102），第一次打开的人只看得到一个"空壳"。比赛/演示场合没人会
 * 真玩到第 21 关，于是最好的东西永远展示不出来。
 *
 * 原则：
 *   1) **可逆**：进入前把相关存档原样快照，退出时逐键还原（原本没有的键删掉，
 *      不留一个伪造的 0 值）。
 *   2) **不骗人**：进入后顶栏常驻「演示中」印章，点一下就退出；
 *      设置页里写清"只改本机进度，退出即还原"。
 *   3) **不写死数据**：要点亮哪些字，从 App.levels 现读，不硬编码字表，
 *      以后改了字表演示模式跟着变。
 *
 * 不碰的东西：设置项、内容包、成就（achieved）—— 那些不是"进度"，
 * 改了会让演示看起来像作弊。
 */
(function () {
  'use strict';

  /* 成就也要一起快照：填进度会立刻触发「成就达成」，
     若不还原，演示一次就永久多出一堆成就，等于造假。 */
  var KEYS = ['wangyi', 'bossraid', 'bonebuild', 'achieved'];
  var SNAP = '__demo_snapshot';

  function active() {
    return App.store.get(SNAP, null) != null;
  }

  /* 第二关：每个区里所有实物都记成"已学"（区在 App.levels.map.zones） */
  function fillWangyi() {
    var zones = (App.levels && App.levels.map && App.levels.map.zones) || [];
    var done = {};
    zones.forEach(function (z) {
      done[z.id] = (z.objects || []).map(function (o) { return o.char; });
    });
    App.store.set('wangyi', { done: done });
    return zones;
  }

  /* 第三关：全部关卡一次通关（perfect 保持为空——"完美"要靠真打）。
     关卡挂在 App.levels.boss.tiers[].list 下，按三阶求和，别写死 21。 */
  function fillBossraid() {
    var n = 0;
    var tiers = (App.levels && App.levels.boss && App.levels.boss.tiers) || [];
    tiers.forEach(function (t) { n += (t.list || []).length; });
    var cleared = [];
    for (var i = 0; i < n; i++) { cleared.push(i); }
    App.store.set('bossraid', { cleared: cleared, perfect: [] });
    return n;
  }

  /* 第一关：把第二关那 61 个字也算成"答对过"，图鉴才不会一半灰 */
  function fillBonebuild(chars) {
    App.store.set('bonebuild', { done: chars });
    return chars.length;
  }

  function enter() {
    if (active()) { return null; }
    var snap = { at: Date.now(), keys: {} };
    KEYS.forEach(function (k) {
      var v = App.store.get(k, null);
      snap.keys[k] = (v === null || v === undefined) ? null : v;
    });
    App.store.set(SNAP, snap);

    var zones = fillWangyi();
    var nLv = fillBossraid();
    var chars = [];
    zones.forEach(function (z) {
      (z.objects || []).forEach(function (o) {
        if (chars.indexOf(o.char) < 0) { chars.push(o.char); }
      });
    });
    fillBonebuild(chars);
    return { zones: zones.length, chars: chars.length, levels: nLv };
  }

  function exit() {
    var snap = App.store.get(SNAP, null);
    if (!snap) { return false; }
    KEYS.forEach(function (k) {
      var v = snap.keys ? snap.keys[k] : null;
      if (v === null || v === undefined) { App.store.del(k); }
      else { App.store.set(k, v); }
    });
    App.store.del(SNAP);
    return true;
  }

  /* 顶栏印章：只在演示中显示，点一下退出并还原。
     注意：切进/切出演示后必须重绘顶栏（App.renderHeader），否则印章要等
     下一次路由切换才出现——实测过，光改存档顶栏不会自己更新。 */
  function refresh() {
    /* 真正的入口挂在 App.shell / App.router 上（App.renderHeader 是 undefined，
       实测过，别照名字猜）：先重绘顶栏，再重绘当前场景。 */
    if (App.shell && App.shell.renderHeader) { App.shell.renderHeader(); }
    if (App.router && App.router.render) { App.router.render(); }
  }

  function badge() {
    if (!active()) { return null; }
    var b = App.el('button', 'seal top-seal demo-seal', '演示中');
    b.type = 'button';
    b.title = '正在演示模式：进度是演示用的，点这里退出并还原';
    b.onclick = function () { exit(); refresh(); };
    return b;
  }

  /* 设置页里的那一块 */
  function panel() {
    var box = App.el('div', 'sect');
    box.appendChild(App.el('h4', null, '演示模式'));
    box.appendChild(App.el('div', 'hint',
      '给演示与评审用：一键把第二关、第三关填成「玩过一阵」的样子，' +
      '图鉴也跟着亮起来，不必真玩 21 关。只改本机进度，' +
      '退出演示即逐键还原（连"原本没有进度"这件事也一起还原）。'));

    var bar = App.el('div', 'bar');
    if (active()) {
      var snap = App.store.get(SNAP, null) || {};
      var when = snap.at ? new Date(snap.at) : null;
      box.appendChild(App.el('div', 'tune',
        when ? ('演示中 —— 进入于 ' + when.toLocaleTimeString()) : '演示中'));
      var out = App.el('button', 'btn sm primary', '退出演示并还原进度');
      out.onclick = function () {
        exit();
        App.toast('已退出演示，进度还原到进入前的样子');
        refresh();
      };
      bar.appendChild(out);
    } else {
      var go = App.el('button', 'btn sm', '进入演示模式');
      go.onclick = function () {
        var r = enter();
        if (!r) { return; }
        App.toast('演示模式：' + r.zones + ' 片区域、' + r.levels + ' 关已填好');
        refresh();
      };
      bar.appendChild(go);
      var tip = App.el('span', 'chip', '不会上传，随时可退出');
      bar.appendChild(tip);
    }
    box.appendChild(bar);
    return box;
  }

  App.demo = { active: active, enter: enter, exit: exit, badge: badge, panel: panel };
})();
