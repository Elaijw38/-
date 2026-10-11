/* 字趣 · 新版壳层验证 —— 开发自查，不参与部署
   由 dev/_run_shell.py 注入 index.html 末尾运行，结果写入 <html> 的 data-report。

   验：
     固定顶栏：四个入口 + 品牌 + 设置，选中态跟随路由
     首页：主视觉、三个真实玩法卡（含真实进度）、每日一字、我的收集
     图鉴：四档计数、筛选、检索、详情浮层开关、合体字的组合示意
     玩法说明：三个玩法各自的步骤
     页脚：玩法入口来自真实玩法表
   硬约束：每次 render 会重建 DOM，动作前必须重新查询节点；全程同步，不排队。 */
(function () {
  'use strict';
  var L = [], errs = [];
  window.addEventListener('error', function (e) { errs.push('ERROR: ' + e.message); });
  function log(s) { L.push(String(s)); }
  function q(s) { return document.querySelector(s); }
  function qa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function txt(e) { return e ? String(e.textContent).trim() : ''; }
  function flag(b) { return b ? '是' : '否'; }
  function go(h) { location.hash = h; }
  function tap(el) {
    if (!el) { return false; }
    if (typeof el.click === 'function') { el.click(); return true; }
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return true;
  }
  function btnByText(re) {
    var l = qa('button, a');
    for (var i = 0; i < l.length; i++) { if (re.test(txt(l[i]))) { return l[i]; } }
    return null;
  }
  function navOn() {
    var a = q('.top-link.on');
    return a ? txt(a) : '（无）';
  }

  function run() {
    var App = window.App;
    try {
      log('=== 一、固定顶栏 ===');
      var links = qa('#siteTop .top-link');
      log('  顶栏入口: ' + links.map(txt).join(' / ') + '（' + links.length + ' 个）');
      log('  品牌在: ' + flag(!!q('#siteTop .top-brand'))
        + '　屏幕阅读器文案: 「' + txt(q('#siteTop .sr-only')) + '」');
      var topRect = q('#siteTop').getBoundingClientRect();
      log('  顶栏 position=' + getComputedStyle(q('#siteTop')).position
        + '　高 ' + Math.round(topRect.height) + 'px（应 sticky／固定顶部）');
      log('  已取消旧左侧功能栏: ' + flag(!q('.app-nav')));

      log('');
      log('=== 二、路由与选中态 ===');
      [['#/home', '主页'], ['#/modes', '开始游戏'], ['#/atlas', '汉字图鉴'], ['#/howto', '玩法说明']]
        .forEach(function (x) {
          go(x[0]);
          App.router.render();
          log('  ' + x[0].padEnd(10) + ' 选中「' + navOn() + '」（应 ' + x[1] + '）'
            + '　场景类=' + (q('.scene') ? q('.scene').className : '?'));
        });
      go('#/play/boss-raid'); App.router.render();
      log('  #/play/…   选中「' + navOn() + '」（对局归入「开始游戏」）');
      go('#/settings'); App.router.render();
      log('  #/settings 选中「' + navOn() + '」');

      log('');
      log('=== 三、首页 ===');
      go('#/home'); App.router.render();
      var st = App.atlas.stats();
      log('  主视觉: ' + flag(!!q('.hero')) + '　标题「' + txt(q('.hero-title')) + '」');
      /* 首屏结构：一屏大图（真骨片照）+ 标题 + CTA + 下滑提示 */
      var bone = q('.hero-bg');
      log('  首屏大图（铺满作背景）: ' + flag(!!bone) + '　来源「' + (bone ? bone.getAttribute('src') : '') + '」');
      log('    object-fit: ' + (bone ? getComputedStyle(bone).objectFit : '?')
        + '　定位: ' + (bone ? getComputedStyle(bone).position : '?'));
      var veilEl = q('.hero-veil');
      log('    压暗层: ' + flag(!!veilEl));
      var hw = bone ? Math.round(bone.getBoundingClientRect().width) : -1;
      log('    大图宽度 ' + hw + ' vs 视口 ' + document.documentElement.clientWidth
        + ' → 是否全幅: ' + flag(hw >= document.documentElement.clientWidth - 2));
      var cap = txt(q('.hero-credit'));
      log('    署名牌: 「' + cap.slice(0, 46) + '…」　含 CC0: '
        + flag(/CC0/.test(cap)) + '　含摄影者: ' + flag(/Gary Todd/.test(cap)));
      var hero = q('.hero');
      var hr = hero ? hero.getBoundingClientRect() : null;
      log('    首屏是否只占一屏: 底边 ' + (hr ? Math.round(hr.bottom) : -1)
        + ' vs 视口 ' + window.innerHeight
        + ' → ' + flag(hr && hr.bottom <= window.innerHeight + 4));
      log('  下滑提示: ' + flag(!!q('.hero-cue')) + '　文案「' + txt(q('.hero-cue')) + '」');
      log('  统计条（在首屏外）: ' + flag(!!q('.stat-band'))
        + '　' + qa('.stat-cell').map(txt).join('　'));
      log('  CTA: ' + qa('.hero-cta a').map(txt).join(' / '));
      var cards = qa('.play-card');
      log('  玩法入口卡: ' + cards.length + '（应等于可玩玩法数 '
        + App.modes.playable().length + '）');
      cards.forEach(function (c) {
        var name = txt(c.querySelector('.pc-title h3'));
        var prog = c.querySelector('.pc-progtext');
        log('    ' + name + '　进度=' + (prog ? txt(prog) : '（无进度数据，不显示）'));
      });
      log('  每日一字: 「' + txt(q('.dc-char')) + '」　构件='
        + txt(q('.dc-comps')) + '　有字形=' + flag(!!q('.dc-ob svg')));
      log('  我的收集: ' + txt(q('.cc-big')).replace(/\s+/g, ' ')
        + '　分档 ' + qa('.cc-kind').map(txt).join('，'));

      log('');
      log('=== 四、图鉴 ===');
      go('#/atlas'); App.router.render();
      log('  总条目: ' + App.atlas.entries().length + '　去重字: ' + st.chars
        + '　已解锁: ' + st.learned);
      var chips = qa('.chipbtn');
      log('  筛选片: ' + chips.map(txt).join(' / '));
      var allCards0 = qa('.atlas-card').length;
      log('  「全部」卡片数: ' + allCards0);
      tap(chips[1]);   /* 构件 */
      log('  点「' + txt(chips[1]) + '」→ 卡片数 ' + qa('.atlas-card').length
        + '　选中态=' + flag(qa('.chipbtn')[1].className.indexOf('on') >= 0));
      tap(qa('.chipbtn')[0]);
      log('  点回「全部」→ 卡片数 ' + qa('.atlas-card').length);
      var search = q('.atlas-search');
      search.value = '日';
      search.oninput();
      log('  检索「日」→ 卡片数 ' + qa('.atlas-card').length
        + '　计数文案「' + txt(q('.atlas-count')) + '」');
      search.value = 'zzz不可能匹配';
      search.oninput();
      log('  检索一个不存在的词 → 空态提示: 「' + txt(q('.atlas-grid .lead')) + '」');
      search.value = ''; search.oninput();
      log('  清空检索 → 卡片数 ' + qa('.atlas-card').length);

      log('');
      log('=== 五、图鉴详情浮层 ===');
      log('  打开前存在浮层: ' + flag(!!q('#atlasSheet')));
      tap(qa('.atlas-card')[0]);
      log('  点第一张卡 → 浮层: ' + flag(!!q('#atlasSheet'))
        + '　标题「' + txt(q('.atlas-sheet .edhead h3')) + '」');
      log('    今字格: 「' + txt(q('.as-char')) + '」　有字形: ' + flag(!!q('.as-glyph')));
      log('    正文行数: ' + qa('.as-line').length + '　状态: 「' + txt(q('.as-state')) + '」');
      log('    去玩法按钮: ' + qa('.as-links a').map(txt).join(' / ') || '（无）');
      tap(btnByText(/^关闭$/));
      log('  点关闭 → 浮层还在: ' + flag(!!q('#atlasSheet')) + '（应「否」）');
      /* 合体字应给组合示意而不是空框 */
      var word = App.atlas.entries().filter(function (e) { return e.kind === 'word'; })[0];
      log('  合体字「' + word.char + '」有整字字形: ' + flag(word.hasGlyph)
        + '　构件: ' + (word.comps || []).join('＋'));
      log('    它的卡片是否画了组合示意: ' + flag(!!q('.atlas-card .composed')));

      log('');
      log('=== 六、玩法说明 ===');
      go('#/howto'); App.router.render();
      var secs = qa('.howto-sec');
      log('  区块数: ' + secs.length + '（3 个玩法 + 通用操作 + 后续玩法 + 资料来源）');
      qa('.howto-head').forEach(function (h) {
        log('    ' + txt(h.querySelector('.howto-name'))
          + '　步骤 ' + h.parentNode.querySelectorAll('.howto-steps li').length + ' 条');
      });
      log('  通用操作条数: ' + qa('.howto-tips li').length);
      log('  资料来源: ' + flag(!!q('.howto-sec .howto-list')));

      log('');
      log('=== 六五、成就与评级 ===');
      go('#/home'); App.router.render();
      var sum0 = App.achievements.summary();
      log('  初始评级: 「' + sum0.rank.name + '」　已达成 ' + sum0.achieved + ' / ' + sum0.total);
      log('  成就项数: ' + qa('.ach-item').length + '（应等于成就总数 '
        + App.achievements.list().length + '）');
      log('  每项都有进度条: ' + flag(qa('.ach-item .ach-bar').length === qa('.ach-item').length));

      /* 真造一份跨玩法进度：王邑 12 处、讨伐 3 关（含 1 完美）、构字 3 张字卡 */
      var wyChars = [];
      ((App.levels.map || {}).zones || []).forEach(function (z) {
        if (wyChars.length >= 12) return;
        (z.objects || []).forEach(function (o) {
          if (wyChars.length < 12) wyChars.push(o.char);
        });
      });
      var wyDone = { '天象': [], '山川': [], '草木': [], '禽兽虫鱼': [], '人居器物': [] };
      var zk = Object.keys(wyDone);
      wyChars.forEach(function (c, i) { wyDone[zk[i % zk.length]].push(c); });
      App.store.set('wangyi', { done: wyDone });
      App.store.set('bossraid', { cleared: [0, 1, 2], perfect: [1] });
      App.store.set('bonebuild', { done: ['明', '休', '采'] });
      /* 清掉成就账，才能观察到"新达成"的弹提示 */
      App.achievements.reset();

      var sum1 = App.achievements.summary();
      var st1 = App.atlas.stats();
      log('  造进度后：收集 ' + sum1.raw.learned + ' / ' + sum1.raw.chars
        + '　王邑 ' + sum1.raw.objDone + '　讨伐 ' + sum1.raw.bossCleared
        + '（完美 ' + sum1.raw.bossPerfect + '）　构字 ' + sum1.raw.cardDone);
      log('  评级: 「' + sum0.rank.name + '」 → 「' + sum1.rank.name + '」'
        + (sum1.rank.name !== sum0.rank.name ? '　✓ 随收集上升' : '　（未变，检查阈值）'));
      log('  下一级: 「' + (sum1.nextRank ? sum1.nextRank.name : '已满级') + '」'
        + (sum1.nextRank ? '，还差 ' + Math.max(0, sum1.nextNeed - sum1.raw.learned) + ' 个字' : ''));

      var first = App.achievements.check();
      log('');
      log('  首次对账（应记为已知、不弹提示）: ' + first.length + ' 项');
      var second = App.achievements.check();
      log('  再次对账（应无新达成）: ' + second.length + ' 项');

      /* 再造一点进度，触发"新达成" */
      App.store.set('bonebuild', { done: ['明', '休', '采', '相', '集', '鸣', '渔', '涉', '析', '焚'] });
      var third = App.achievements.check();
      log('  补足构字到 10 张 → 新达成 ' + third.length + ' 项: '
        + third.map(function (a) { return a.name; }).join('、'));

      go('#/home'); App.router.render();
      log('');
      log('  首页复检:');
      log('    评级: 「' + txt(q('.cc-rankname')) + '」');
      log('    已达成计数: 「' + txt(q('.ach-card .dc-date')) + '」');
      log('    达成项（带 .done）: ' + qa('.ach-item.done').length + ' 项');
      log('    达成项名: ' + qa('.ach-item.done .ach-name').map(txt).join('、') || '（无）');
      log('    有进度条的项: ' + qa('.ach-item .ach-fill').length
        + '　其中宽度非 0: ' + qa('.ach-item .ach-fill').filter(function (f) {
            return parseFloat(f.style.width) > 0;
          }).length);

      log('');
      log('=== 六六、图鉴「已解锁」筛选 ===');
      go('#/atlas'); App.router.render();
      var got = qa('.chipbtn').filter(function (b) { return /已解锁/.test(txt(b)); })[0];
      log('  「已解锁」筛选片在: ' + flag(!!got) + '　文案「' + txt(got) + '」');
      var allN = qa('.atlas-card').length;
      tap(got);
      var gotN = qa('.atlas-card').length;
      log('  点它 → 卡片 ' + allN + ' → ' + gotN
        + '（应等于片子上的数字，也就是条目数）');
      log('  片子上的数字与结果一致: ' + flag(/\d+/.test(txt(got)) &&
        parseInt(/(\d+)/.exec(txt(got))[1], 10) === gotN));
      log('  选中态: ' + flag(qa('.chipbtn').some(function (b) {
        return /已解锁/.test(txt(b)) && b.className.indexOf('on') >= 0;
      })));
      log('  已解锁的卡片带 .got: ' + qa('.atlas-card.got').length + '（应等于 ' + gotN + '）');
      tap(qa('.chipbtn')[0]);
      log('  点回「全部」→ ' + qa('.atlas-card').length);
      /* 收尾：把造的进度清掉，别污染后续小节 */
      App.store.del('wangyi'); App.store.del('bossraid'); App.store.del('bonebuild');
      App.achievements.reset();

      log('');
      log('=== 七、页脚 ===');
      go('#/home'); App.router.render();
      var footLinks = qa('#footModes a');
      log('  玩法入口: ' + footLinks.map(txt).join(' / '));
      log('  版本号: 「' + txt(q('#footVer')) + '」');
      log('  含字形署名: ' + flag(/hanzi-glyphs-svg/.test(txt(q('.footer')))));
      log('  含底图出处: ' + flag(/Agnes/.test(txt(q('.footer')))));

      log('');
      log('=== 八、三个玩法仍可用 ===');
      App.modes.playable().forEach(function (m) {
        go('#/play/' + m.id); App.router.render();
        var host = q('.mode-host');
        var hasErr = /加载出错|尚未实现/.test(txt(host));
        log('  ' + m.id.padEnd(12) + ' 挂载: ' + flag(!!host && host.children.length > 0)
          + '　报错: ' + flag(hasErr) + '　宽版式: '
          + flag(!!q('.app-shell.layout-wide')));
      });

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
    if (window.__ZQ__ && window.App && window.App.router && window.App.atlas) { run(); return; }
    if (tries > 200) {
      log('!! 平台未就绪');
      document.documentElement.setAttribute('data-report', L.join('\n'));
      return;
    }
    setTimeout(boot, 20);
  }
  boot();
})();
