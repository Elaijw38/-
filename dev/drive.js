/* 字趣 · 浏览器内功能驱动（开发自查用，不参与部署）
   由 dev/_run_drive.py 拷贝到项目根目录后，作为最后一个 <script> 加载。
   结果写入 <html> 的 data-report 属性，便于 headless Edge 的 --dump-dom 取回。 */
(function () {
  'use strict';
  var L = [], errs = [];

  window.addEventListener('error', function (e) {
    errs.push('ERROR: ' + e.message + ' @' + String(e.filename || '').split('/').pop() + ':' + e.lineno);
  });

  function log(s) { L.push(s); }
  function q(s) { return document.querySelector(s); }
  function qa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function byText(sel, re) { return qa(sel).filter(function (b) { return re.test(b.textContent); })[0]; }
  function click(el) { if (!el) return false; el.click(); return true; }
  function trim(s, n) { s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n) + '…' : s; }

  function run() {
    try { realRun(); }
    catch (e) { log('!! DRIVER EXCEPTION: ' + (e && e.message ? e.message : e)); }
    log('');
    log('=== 控制台错误 ===');
    log(errs.length ? errs.join('\n') : '(无)');
    document.documentElement.setAttribute('data-report', L.join('\n'));
  }

  function realRun() {
    var App = window.App;

    log('=== 模块就绪 ===');
    log('window.App: ' + (!!App));
    if (App) {
      log('store/packs/modes/router/shell: ' +
        [!!App.store, !!App.packs, !!App.modes, !!App.router, !!App.shell].join(' / '));
      log('已注册模式: ' + (App.modes ? App.modes.count() : 'n/a') +
          '　内容包类型: ' + (App.packs ? App.packs.types().join(',') : 'n/a'));
      log('品牌字形长度: ' + String(App.brandGlyphURI || '').length);
    }
    log('__ZQ__: ' + (!!window.__ZQ__) +
        '　data-theme: ' + document.documentElement.getAttribute('data-theme') +
        '　App.theme: ' + (App.theme ? '仍存在（应为空）' : '已移除'));
    var obp = getComputedStyle(document.documentElement).getPropertyValue('--ob-pattern') || '';
    log('底纹 --ob-pattern: ' + obp.trim().length + ' 字符');
    if (!App || !App.router || !App.modes || App.modes.count() === 0) {
      log('!! 平台未就绪，跳过后续');
      return;
    }

    log('');
    log('=== 首页 ===');
    log('首页卡片: ' + qa('.home-card').length + qa('.home-card').map(function (c) {
      return '\n   - ' + trim((c.querySelector('h3') || {}).textContent, 12) + '  |  ' +
        trim((c.querySelector('.hc-note') || {}).textContent, 40);
    }).join(''));

    log('');
    log('=== 玩法列表 ===');
    location.hash = '#/modes';
    App.router.render();
    log('模式卡: ' + qa('.mode-card').length + qa('.mode-card').map(function (c) {
      return '\n   - ' + trim((c.querySelector('h3') || {}).textContent, 12) + '  ' +
        (c.classList.contains('pending') ? '[筹备中]' : '[可玩]');
    }).join(''));
    var ready = qa('.mode-card:not(.pending)')[0];
    if (!ready) { log('!! 无可玩模式'); return; }

    log('');
    log('=== 玩法设置页（单人）===');
    click(ready);
    App.router.render();
    log('分区: ' + qa('.setup .sect h4').map(function (h) { return h.textContent.trim(); }).join(' / '));
    log('滑块: ' + qa('.setup input[type=range]').length + '　下拉: ' + qa('.setup select').length);

    var opts = qa('.setup .opts .opt');
    if (opts[1]) click(opts[1]);
    log('切双人后分区: ' + qa('.setup .sect h4').map(function (h) { return h.textContent.trim(); }).join(' / '));
    log('切双人后滑块: ' + qa('.setup input[type=range]').length);

    log('');
    log('=== 对局 ===');
    click(byText('.setup .bar .btn', /开始/));
    log('比分板人数: ' + qa('.scoreboard .pl').length);
    log('字卡: ' + trim((q('#mpGlyph') || {}).textContent, 4) +
        '　星级: ' + trim((q('#mpStars') || {}).textContent, 4));
    log('构件台: ' + qa('#mpPieces .piece').length + ' 件　名角标: ' + qa('#mpPieces .piece .n').length + ' 个');
    log('放置槽: ' + qa('#mpSlots .slot').length + ' 个');
    log('计时: ' + trim((q('#mpClock') || {}).textContent, 4) + ' 秒　回合 ' +
        trim((q('#mpRound') || {}).textContent, 4) + '　轮到 ' + trim((q('#mpTurn') || {}).textContent, 4));
    log('按钮: ' + qa('.info .bar .btn').map(function (b) { return trim(b.textContent, 10); }).join(' / '));

    var pcs = qa('#mpPieces .piece');
    click(pcs[0]);
    log('');
    log('点第 1 件 → 已填 ' + qa('#mpSlots .slot.filled').length +
        '　used 标记: ' + (q('#mpPieces .piece.used') ? '有' : '无'));
    click(pcs[1]);
    log('点第 2 件 → 已填 ' + qa('#mpSlots .slot.filled').length);
    /* 按钮文案：契刻（提交）/ 重摆（清空）/ 卜辞提示 / 质问 */
    click(byText('.info .bar .btn', /重摆|清空/));
    log('重摆 → 已填 ' + qa('#mpSlots .slot.filled').length);

    /* 真甲骨字形的断言 —— 这个玩法叫「甲骨构字」，早先却把今字换个
       等宽字体冒充甲骨文（.g.ob 只写了 font-family:"Courier New"）。
       现在构件台与字卡都出内联 SVG 真字形，这里盯着别退化。 */
    log('');
    log('=== 真甲骨字形 ===');
    log('构件台里带甲骨 SVG 的件数: ' + qa('#mpPieces .piece svg').length +
        ' / ' + qa('#mpPieces .piece').length + ' 件');
    var compSvgs = qa('#mpGlyph .obcomp svg').length;
    log('字卡上的构件组合件数: ' + compSvgs +
        '（合体字应为 2；单构件字走 .glyphone）');
    log('字卡单字形 .glyphone: ' + qa('#mpGlyph .glyphone').length);
    log('字卡今字角标 mpGlyphCap: 「' + trim((q('#mpGlyphCap') || {}).textContent, 6) + '」');

    /* 按当前字卡的构件组成去点，才能拼对拿到正的甲骨片得分。
       字卡现在出的是甲骨形（无文字），今字在 #mpGlyphCap；
       构件台每件下方必有 .n 今字角标，所以按角标匹配最稳。 */
    var need = [], allPieces = [];
    /* 答对之前先记一笔收集数，提交后再比——用来验证进度真的落盘了 */
    var learnedBefore = App.atlas.stats().learned;
    var curChar = String((q('#mpGlyphCap') || {}).textContent || '').trim();
    (function () {
      var capEl = q('#mpGlyphCap');
      var g = capEl ? String(capEl.textContent).trim() : '';
      if (!g) { g = String((q('#mpGlyph') || {}).textContent || '').trim(); }
      var cards = [];
      try {
        if (window.App && App.packs && App.packs.byType) {
          App.packs.byType('cards').forEach(function (pk) {
            var d = (pk && pk.data) || {};
            cards = cards.concat(d.cards || []);
            allPieces = allPieces.concat(d.pieces || []);
          });
        }
      } catch (e) { log('读内容包出错: ' + e.message); }
      var c = cards.filter(function (x) { return x && x.g === g; })[0];
      if (c) need = String(c.w || '').split('+').filter(Boolean);
      if (g) { curChar = g; }
      log('字卡=' + g + ' 所需构件=[' + need.join('＋') + ']');
    })();
    /* 找台上那一件：优先用 .n 今字角标，退回整块文本 */
    var pcAll = qa('#mpPieces .piece');
    var picked = [];
    need.forEach(function (nm) {
      var hit = pcAll.filter(function (p) {
        var nEl = p.querySelector('.n');
        var txt = nEl ? String(nEl.textContent).trim()
                      : String(p.textContent || '').replace(/\s+/g, '');
        return txt === nm && picked.indexOf(p) < 0;
      })[0];
      if (hit) { picked.push(hit); }
    });
    if (picked.length !== need.length) {
      log('（未配全构件，退回点前两件）');
      picked = pcAll.slice(0, 2);
    }
    picked.forEach(click);
    log('按「' + (need.join('＋') || '前两件') + '」点入 → 已填 ' +
        qa('#mpSlots .slot.filled').length);

    click(byText('.info .bar .btn', /契刻|呈上/));
    log('');
    log('提交判定: ' + trim((q('#mpVerdict') || {}).textContent, 60));
    /* 答对后应当揭晓「玩家自己组出的甲骨形」——
       这是"给构件、让玩家自己组、组成了才亮出来"的关键一步。
       题面（字卡）不预先显示它，否则等于给答案。 */
    log('揭晓区 .reveal: ' + qa('#mpVerdict .reveal').length +
        ' 个　其中的甲骨构件: ' + qa('#mpVerdict .reveal .obcomp svg').length + ' 件');
    /* 拼对后界面会立刻转入下一张字卡并重建比分板，抢读分数时序不稳
       （会读到空值或旧值），故不在此断言得分。甲骨片得分的渲染
       由 dev/_preview_bone.html 单独验证。 */
    log('得分渲染: 见 dev/_preview_bone.html');

    /* ---------- 进度落盘（答对过的字进收集） ---------- */
    var bb = App.store.get('bonebuild', null);
    var doneList = (bb && bb.done) ? bb.done : [];
    log('');
    log('=== 进度落盘 ===');
    log('  ziqu.bonebuild = [' + doneList.join('、') + ']');
    log('  本轮字卡「' + curChar + '」已记入: ' +
        (doneList.indexOf(curChar) >= 0 ? '是' : '否'));
    var stA = App.atlas.stats();
    log('  图鉴已解锁: ' + learnedBefore + ' → ' + stA.learned + ' / ' + stA.chars +
        (stA.learned > learnedBefore ? '（+1，落盘生效）' : '（未变）'));
    /* 去重是 markLearned 的职责，这里只检查"存下来的没有重复"这个不变量。
       （早先这段写成"手动 push 一个重复值再看长度变不变"——
         那绕过了去重逻辑，测的是测试自己，不是产品。） */
    (function () {
      var uniq = doneList.filter(function (x, i) { return doneList.indexOf(x) === i; });
      log('  存储去重不变量: 共 ' + doneList.length + ' 条，去重后 ' + uniq.length +
          ' 条 → ' + (uniq.length === doneList.length ? '无重复 ✓' : '有重复 ✗'));
    })();
    log('  收集档位（图鉴四档）: ' + App.atlas.KINDS.map(function (k) {
      var b = stA.byKind[k.id] || { total: 0, learned: 0 };
      return k.name + ' ' + b.learned + '/' + b.total;
    }).join('　'));

    var hb = byText('.info .bar .btn', /提示/);
    if (hb && !hb.disabled) {
      click(hb);
      log('提示后判定: ' + trim((q('#mpVerdict') || {}).textContent, 50));
    } else {
      log('提示按钮不可用（当前难度禁用）——符合预期');
    }
    tail();

    /* 收尾两页（设置 / 筹备中） */
    function tail() {
      log('');
      log('=== 全局设置页 ===');
      location.hash = '#/settings';
      App.router.render();
      log('分区: ' + qa('.scene .sect h4').map(function (h) { return h.textContent.trim(); }).join(' / '));
      log('内容包行数: ' + qa('.scene table tr').length);
      log('主题选项: ' + qa('.scene select option').map(function (o) { return o.textContent; }).join(' / '));

      log('');
      log('=== 筹备中玩法页 ===');
      location.hash = '#/plan';
      App.router.render();
      log('表格行: ' + qa('.scene table tr').length);
    }
  }

  /* 轮询等待平台就绪（boot 在任何驱动脚本之前同步执行） */
  var tries = 0;
  (function wait() {
    tries++;
    if (window.__ZQ__ && window.App && window.App.router) { run(); return; }
    if (tries > 160) { run(); return; }
    setTimeout(wait, 20);
  })();
})();
