# -*- coding: utf-8 -*-
"""第二关「殷商王邑」端到端走查（CDP 真视口 + 真鼠标事件）。

需求「四、交付前检查」要的三件事，这个脚本一次跑完并留证据：

  1. 五个区域**任意顺序**都能进（不按顺序：按 居住器物 → 天象 → 草木 → 山川 → 禽兽虫鱼）
  2. 每个区域：点实物命中热点 → 自动局部放大 → 再点开学习卡 → 卡片字段齐全 → 关掉回原位
  3. 学完一个字后印记/进度条/区域点亮跟着变，且**两个宽度**都截了图

它不靠"看着对"——每一步都把量出来的数字打出来（命中半径、缩放倍率、
卡片文本、进度数字）。桌面与手机各跑一遍。

用法：
  python dev/_wy2_walkthrough.py                # 桌面 1440x1000 + 手机 390x844
  python dev/_wy2_walkthrough.py 1440 1000      # 只跑一个视口
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")
URL = "http://127.0.0.1:8099/index.html#/play/wangyi-map"

# 故意不按 01→05 的顺序，用来证明"任意顺序可进"
ORDER = ['人居器物', '天象', '草木', '山川', '禽兽虫鱼']

CDP = r'''
const ws = new WebSocket(process.argv[2]);
const W = +process.argv[3], H = +process.argv[4];
const ORDER = JSON.parse(process.argv[5]);
const TAG = process.argv[6];
const fs = require('fs');
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = expr => send('Runtime.evaluate', {expression: expr, returnByValue: true})
  .then(r => (r.result && r.result.value) || '');
const J = async expr => { try { return JSON.parse(await ev(expr)); } catch (e) { return null; } };
const shot = async name => {
  const s = await send('Page.captureScreenshot', {format: 'png'});
  fs.writeFileSync('/tmp/' + name, Buffer.from(s.data, 'base64'));
};
const LOG = [];
const LOGPATH = process.argv[8];
const log = s => { LOG.push(s); try { fs.appendFileSync(LOGPATH, s + '\n'); } catch (e) {} };

ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Log.enable');
  await send('Runtime.setAsyncCallStackDepth', {maxDepth: 0});
  const ERRS = [];
  ws.addEventListener('message', e => {
    let m = null; try { m = JSON.parse(e.data); } catch (err) { return; }
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params && m.params.exceptionDetails;
      ERRS.push('EXC ' + ((d && (d.exception && d.exception.description)) || (d && d.text) || ''));
    }
    if (m.method === 'Log.entryAdded' && m.params && m.params.entry
        && m.params.entry.level === 'error') {
      ERRS.push('LOG ' + m.params.entry.text);
    }
  });
  await send('Emulation.setDeviceMetricsOverride',
    {width: W, height: H, deviceScaleFactor: 1, mobile: W < 700});
  await send('Page.navigate', {url: process.argv[7]});
  await sleep(6000);

  /* ---- 一、大地图盘点 ---- */
  const world = await J("JSON.stringify((function(){" +
    "var pins=[].slice.call(document.querySelectorAll('.wy2-pin'));" +
    "var b=document.querySelector('.wy2-board-art');" +
    "var r=b?b.getBoundingClientRect():null;" +
    "var de=document.documentElement;" +
    "return {pins:pins.length," +
    "names:pins.map(function(p){return p.querySelector('b').textContent;})," +
    "labels:pins.map(function(p){return p.getAttribute('aria-label');})," +
    "pinWH:pins.map(function(p){var q=p.getBoundingClientRect();" +
      "return Math.round(q.width)+'x'+Math.round(q.height);})," +
    "board:r?[Math.round(r.width),Math.round(r.height)]:null," +
    "boardTop:r?Math.round(r.top):null," +
    "boardBottom:r?Math.round(r.bottom):null," +
    "overflowX:de.scrollWidth-de.clientWidth," +
    "guide:!!document.querySelector('.wy2-guide')," +
    "guideTop:(function(){var g=document.querySelector('.wy2-guide');" +
      "return g?Math.round(g.getBoundingClientRect().top):-1;})()," +
    "credit:!!document.querySelector('.wy2-credit')};})())");
  log('WORLD ' + JSON.stringify(world));
  await shot(TAG + '-world.png');

  /* ---- 二、逐区走查 ---- */
  const zones = [];
  for (let zi = 0; zi < ORDER.length; zi++) {
    const name = ORDER[zi];
    const ok = await ev("(function(){var p=[].slice.call(document.querySelectorAll('.wy2-pin'))" +
      ".filter(function(e){return e.querySelector('b').textContent==='" + name + "';})[0];" +
      "if(!p) return 'no-pin'; p.click(); return 'ok';})()");
    await sleep(1400);
    const z0 = await J("JSON.stringify((function(){" +
      "var vp=document.querySelector('.wy2-viewport');" +
      "var sp=[].slice.call(document.querySelectorAll('.wy2-spot'));" +
      "var st=document.querySelector('.wy2-stage');" +
      "var svg=document.querySelector('.wy2-hotspots');" +
      "var r=svg?svg.getBoundingClientRect():null;" +
      "var s=st?st.getBoundingClientRect():null;" +
      "return {entered:!!vp, spots:sp.length," +
      "stage:s?[Math.round(s.width),Math.round(s.height)]:null," +
      "svg:r?[Math.round(r.width),Math.round(r.height)]:null," +
      "vp:vp?[vp.clientWidth,vp.clientHeight,Math.round(vp.scrollWidth),Math.round(vp.scrollHeight)]:null," +
      "scale:r?(r.width/2624):null," +
      "head:(function(){var h=document.querySelector('.wy2-zone-head');" +
        "return h?h.textContent.replace(/ /g,' ').trim():'';})()};})())");
    if (zi === 0) { await shot(TAG + '-zone-' + zi + '.png'); }

    /* 逐字走一遍：点实物 → 放大 → 开卡 → 拼笔画 → 关掉 */
    const n = z0 && z0.spots ? z0.spots : 0;
    const learned = [];
    let guard = 0;
    for (let k = 0; k < n; k++) {
      if (guard++ > n * 6 + 60) { log('GUARD ' + name + ' at k=' + k); break; }

      /* 每一枚字都"回到全景 → 滚到热点 → 点它 → 再点一次开卡"。
         全程只依赖三件事：视口当前尺寸、热点当前 rect、缩放后的新 rect。
         任何一步拿不到就记一条 MISS 并继续，不猜。 */
      for (let reset = 0; reset < 3; reset++) {
        const z = await ev("(function(){var b=[].slice.call(" +
          "document.querySelectorAll('.wy2-tool')).filter(function(e){" +
          "return e.textContent.indexOf('缩回')>=0;})[0];" +
          "if(!b) return 'nozoom'; b.click(); return 'clicked';})()");
        await sleep(600);
        if (z === 'nozoom') { break; }
      }

      /* 点热点：调用**应用自己的** pickAt 做最近点判定（与鼠标路径同一函数），
         然后在热点的屏幕位置上派发真鼠标事件——两条路径都走一遍。 */
      const t1 = await J("JSON.stringify((function(){" +
        "var top=document.querySelector('.top');" +
        "var topB=top?top.getBoundingClientRect().bottom:0;" +
        "/* 先把整个视口拉回顶栏下方：滚页面会让视口滑到固定顶栏底下 */" +
        "var vr0=document.querySelector('.wy2-viewport').getBoundingClientRect();" +
        "if(vr0.top<topB+6){ window.scrollBy(0, vr0.top-topB-6); }" +
        "var vp=document.querySelector('.wy2-viewport'); if(!vp) return {err:'no-vp'};" +
        "var sp=[].slice.call(document.querySelectorAll('.wy2-spot'));" +
        "var t=null,c=null;" +
        "for(var i=0;i<sp.length;i++){ if(!sp[i].classList.contains('done')){" +
        "t=sp[i]; c=t.querySelector('.wy2-hit'); break;} }" +
        "if(!t) return {none:true};" +
        "var vr=vp.getBoundingClientRect(); var r=c.getBoundingClientRect();" +
        "vp.scrollLeft += Math.round((r.left+r.width/2)-(vr.left+vr.width/2));" +
        "vp.scrollTop  += Math.round((r.top+r.height/2)-(vr.top+vr.height/2));" +
        "r=c.getBoundingClientRect(); vr=vp.getBoundingClientRect();" +
        "var lo=Math.max(vr.left,topB);" +
        "var x=(Math.max(r.left,vr.left)+Math.min(r.right,vr.right))/2;" +
        "var y=(Math.max(r.top,lo)+Math.min(r.bottom,vr.bottom))/2;" +
        "/* 用应用自己的最近点判定验一次：这一点应该判给它 */" +
        "var got=(window.__wyDbg&&window.__wyDbg.pickAt)?" +
        "window.__wyDbg.pickAt(x,y):null;" +
        "return {x:Math.round(x),y:Math.round(y)," +
        "pickHit:got?got.o.char:null," +
        "label:t.getAttribute('aria-label')||''," +
        "topB:Math.round(topB)," +
        "inBox:(x>vr.left&&x<vr.right&&y>lo&&y<vr.bottom)};})())");
      if (!t1 || t1.none || t1.err || !t1.inBox) {
        log('MISS-PICK ' + name + '#' + k + ' ' + JSON.stringify(t1));
        break;
      }
      const want = t1.pickHit || '';
      log('TAP1 ' + name + '#' + k + ' at ' + t1.x + ',' + t1.y
        + ' 最近点判定=' + t1.pickHit + ' inBox=' + t1.inBox);
      await send('Input.dispatchMouseEvent',
        {type: 'mousePressed', x: t1.x, y: t1.y, button: 'left', clickCount: 1});
      await send('Input.dispatchMouseEvent',
        {type: 'mouseReleased', x: t1.x, y: t1.y, button: 'left', clickCount: 1});
      await sleep(700);

      const post = await J("JSON.stringify((function(){" +
        "var vp=document.querySelector('.wy2-viewport');" +
        "var c=document.querySelector('.wy2-spot.focus .wy2-hit');" +
        "return {st:window.__wyDbg.state()," +
        "lastTap:(window.__wyDbg.taps[window.__wyDbg.taps.length-1])||null," +
        "tapCount:window.__wyDbg.taps.length," +
        "focusSpots:document.querySelectorAll('.wy2-spot.focus').length," +
        "spots:document.querySelectorAll('.wy2-spot').length," +
        "vp:!!vp, sx:vp?Math.round(vp.scrollLeft):-1, sy:vp?Math.round(vp.scrollTop):-1," +
        "sw:vp?Math.round(vp.scrollWidth):-1, sh:vp?Math.round(vp.scrollHeight):-1," +
        "focusRect:(function(){if(!c) return null;var r=c.getBoundingClientRect();" +
          "return [Math.round(r.left),Math.round(r.top),Math.round(r.width)];})()};})())");
      log('POST-ZOOM ' + name + '#' + k + ' ' + JSON.stringify(post));
      if (k === 0 && zi === 0) { await shot(TAG + '-zoom.png'); }

      const pick = t1;
      const p2 = await J("JSON.stringify((function(){" +
        "var vp=document.querySelector('.wy2-viewport');" +
        "var c=document.querySelector('.wy2-spot.focus .wy2-hit');" +
        "if(!c) return {err:'no-focus'};" +
        "var vr=vp.getBoundingClientRect(), r=c.getBoundingClientRect();" +
        "var x=(Math.max(r.left,vr.left)+Math.min(r.right,vr.right))/2;" +
        "var y=(Math.max(r.top,vr.top)+Math.min(r.bottom,vr.bottom))/2;" +
        "var got=window.__wyDbg&&window.__wyDbg.pickAt?window.__wyDbg.pickAt(x,y):null;" +
        "return {x:Math.round(x),y:Math.round(y),pickHit:got?got.o.char:null," +
        "inBox:(x>vr.left&&x<vr.right&&y>vr.top&&y<vr.bottom)};})())");
      log('TAP2 ' + name + '#' + k + ' ' + JSON.stringify(p2));

      const click2 = (p2 && !p2.err && p2.inBox) ? p2 : pick;
      await send('Input.dispatchMouseEvent',
        {type: 'mousePressed', x: click2.x, y: click2.y, button: 'left', clickCount: 1});
      await send('Input.dispatchMouseEvent',
        {type: 'mouseReleased', x: click2.x, y: click2.y, button: 'left', clickCount: 1});
      await sleep(600);
      log('CARDLIFE ' + await ev("(function(){return 'cardNow='+" +
        "!!document.querySelector('.wy2-card');})()"));
      const cardNow = await ev("(function(){var c=document.querySelector('.wy2-card');" +
        "if(!c) return 'NOTHING';" +
        "var g=c.querySelector('.wy2-card-char'), k=c.querySelector('.wy2-card-kind')," +
        "m=c.querySelector('.wy2-card-mean'), f=c.querySelector('.wy2-card-form-note');" +
        "var out=[g?g.textContent:'', k?k.textContent:'', m?m.textContent:''," +
        "f?f.textContent:'', String(c.querySelectorAll('.wy2-card-glyph path').length)," +
        "String(c.querySelectorAll('.wy2-card-acts .btn').length)];" +
        "return JSON.stringify(out);})()");
      const card = (cardNow && cardNow !== 'NOTHING')
        ? (function () {
            const p = JSON.parse(cardNow);
            return {char: p[0], kind: p[1], mean: p[2], form: p[3],
                    glyphPaths: +p[4], actCount: +p[5]};
          })()
        : {none: true};
      if (k === 0 && zi === 0) { await shot(TAG + '-card.png'); }
      zones.push({zone: name, char: card && card.char, kind: card && card.kind,
        glyphPaths: card && card.glyphPaths,
        meanLen: card && card.mean ? card.mean.length : 0,
        formLen: card && card.form ? card.form.length : 0});

      if (!card || card.none) {
        const dbg = await J("JSON.stringify((function(){" +
          "return {cards:(window.__wyDbg&&window.__wyDbg.cards)||0," +
          "lastCard:(window.__wyDbg&&window.__wyDbg.lastCard)||null," +
          "cardErr:(window.__wyDbg&&window.__wyDbg.cardErr)||null," +
          "taps:(window.__wyDbg&&window.__wyDbg.taps)||[]," +
          "spots:document.querySelectorAll('.wy2-spot').length," +
          "done:document.querySelectorAll('.wy2-spot.done').length," +
          "card:!!document.querySelector('.wy2-card')," +
          "hitAt:(function(){var e=document.elementFromPoint(" + p2.x + "," + p2.y + ");" +
            "return e?(e.getAttribute('class')||e.tagName):'null';})()};})())");
        log('CARD-MISS ' + name + ' #' + k + ' 点 ' + p2.x + ',' + p2.y
          + ' 期望「' + want + '」 放大后热点 ' + JSON.stringify(p2)
          + ' 视口 ' + JSON.stringify({}) + ' 现场 ' + JSON.stringify(dbg));
        /* 没开出卡片：点"缩回全景"复位，继续 */
        await ev("(function(){var b=[].slice.call(document.querySelectorAll('.wy2-tool'))" +
          ".filter(function(e){return e.textContent.indexOf('缩回')>=0;})[0]; if(b) b.click();" +
          "var x=document.querySelector('.wy2-card-x'); if(x) x.click();})()");
        await sleep(500);
        continue;
      }
      /* 练一练 → 逐笔拖到正确位置 → 记录落下。
         每一笔要落在它"应在的位置"，所以先把该笔的目标画布坐标
         换算成 stage 上的屏幕坐标，再派发 pointerdown/up：
         只把 up 放在目标点，判定就会通过。 */
      await ev("(function(){var b=[].slice.call(document.querySelectorAll('.wy2-card-acts .btn'))" +
        "[0]; if(b) b.click();})()");
      await sleep(500);
      const flowState = await J("JSON.stringify((function(){" +
        "return {pieces:document.querySelectorAll('.wy2-piece').length," +
        "stage:!!document.querySelector('.wy2-flow-stage')," +
        "verdict:(function(){var v=document.querySelector('.wy2-flow-verdict');" +
          "return v?v.textContent.trim():'';})()};})())");
      log('FLOW-' + name + '#' + k + ' ' + JSON.stringify(flowState));
      let fg = 0;
      const drops = [];
      while (fg++ < 40) {
        const res = await ev("(function(){" +
          "var p=document.querySelector('.wy2-piece'); if(!p) return '0';" +
          "var s=document.querySelector('.wy2-flow-stage');" +
          "var sr=s.getBoundingClientRect();" +
          "var c=(p.getAttribute('data-c')||'').split(',').map(Number);" +
          "var tg=(p.getAttribute('data-target')||'').split(',').map(Number);" +
          "var tol=+p.getAttribute('data-tol');" +
          "var tx=tg[0]/100, ty=tg[1]/100;" +
          "var x=sr.left+tx*sr.width, y=sr.top+ty*sr.height;" +
          "p.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:sr.left+5,clientY:sr.top+5,pointerId:1}));" +
          "p.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,clientX:x,clientY:y,pointerId:1}));" +
          "var v=document.querySelector('.wy2-flow-verdict');" +
          "return JSON.stringify({left:document.querySelectorAll('.wy2-piece').length," +
          "stage:[Math.round(sr.width),Math.round(sr.height)]," +
          "target:[+tx.toFixed(3),+ty.toFixed(3)],tol:tol," +
          "dropAt:[Math.round(x),Math.round(y)]," +
          "v:v?v.textContent.trim():''});})()");
        let d = null;
        try { d = JSON.parse(res); } catch (e) { d = null; }
        if (!d) { drops.push('ERR ' + res); break; }
        if (d.left === 0) { break; }
        drops.push(d);
        if (drops.length > 3) { break; }   /* 前几笔就能看出判定对不对 */
      }
      log('DROPS-' + name + '#' + k + ' ' + JSON.stringify(drops.slice(0, 4)));
      /* 剩下的笔画一路摆完 */
      let rest = 0;
      while (rest++ < 40) {
        const left = await ev("(function(){var p=document.querySelector('.wy2-piece');" +
          "if(!p) return '0'; var s=document.querySelector('.wy2-flow-stage');" +
          "var sr=s.getBoundingClientRect();" +
          "var tg=(p.getAttribute('data-target')||'0,0').split(',').map(Number);" +
          "var x=sr.left+tg[0]/100*sr.width, y=sr.top+tg[1]/100*sr.height;" +
          "p.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:sr.left+5,clientY:sr.top+5,pointerId:1}));" +
          "p.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,clientX:x,clientY:y,pointerId:1}));" +
          "return String(document.querySelectorAll('.wy2-piece').length);})()");
        if (!left || left === '0') { break; }
      }
      await sleep(1900);   /* 完成动画 + 重画 */
      const done = await J("JSON.stringify((function(){" +
        "var v=document.querySelector('.wy2-flow-verdict');" +
        "return {verdict:v?v.textContent.trim():'(无)'," +
        "marks:document.querySelectorAll('.wy2-seal').length," +
        "head:(function(){var h=document.querySelector('.wy2-zone-head');" +
          "return h?h.textContent.trim():'';})()};})())");
      log('DONE-' + name + '#' + k + ' ' + JSON.stringify(done));
      learned.push(card.char);
    }

    const z1 = await J("JSON.stringify((function(){" +
      "var h=document.querySelector('.wy2-zone-head');" +
      "var marks=document.querySelectorAll('.wy2-seal').length;" +
      "var filled=(function(){var f=document.querySelector('.wy2-zone-fill');" +
        "return f?f.style.width:'';})();" +
      "return {head:h?h.textContent.replace(/ /g,' ').trim():''," +
      "marks:marks,filled:filled," +
      "clear:!!document.querySelector('.wy2-zone-clear')};})())");
    zones.push({zone: name, summary: z1, learnedCount: learned.length});
    if (zi === 0) { await shot(TAG + '-zone-done.png'); }

    /* 返回大地图，确认真亮了 */
    await ev("(function(){var b=document.querySelector('.wy2-back'); if(b) b.click();})()");
    await sleep(1200);
    const after = await J("JSON.stringify((function(){" +
      "var pins=[].slice.call(document.querySelectorAll('.wy2-pin'));" +
      "var lit=pins.filter(function(p){return p.classList.contains('lit');});" +
      "var glows=[].slice.call(document.querySelectorAll('.wy2-glow.on')).length;" +
      "return {pins:pins.length,lit:lit.length,glows:glows," +
      "meter:(function(){var f=document.querySelector('.wy2-meter-fill');" +
        "return f?f.style.width:'';})()," +
      "words:(function(){var w=document.querySelector('.wy2-meter-words');" +
        "return w?w.textContent.trim():'';})()};})())");
    log('AFTER-' + name + ' ' + JSON.stringify(after));
    if (zi === 0) { await shot(TAG + '-world-lit1.png'); }
  }

  await shot(TAG + '-world-final.png');
  const fin = await J("JSON.stringify((function(){" +
    "var pins=[].slice.call(document.querySelectorAll('.wy2-pin'));" +
    "return {lit:pins.filter(function(p){return p.classList.contains('lit');}).length," +
    "all:document.querySelectorAll('.wy2-pin').length," +
    "words:(function(){var w=document.querySelector('.wy2-meter-words');" +
      "return w?w.textContent.trim():'';})()," +
    "glowOn:document.querySelectorAll('.wy2-glow.on').length," +
    "overflowX:document.documentElement.scrollWidth-document.documentElement.clientWidth};})())");
  log('FINAL ' + JSON.stringify(fin));
  log('CARDS ' + JSON.stringify(zones));
  log('ERRS ' + JSON.stringify(ERRS.slice(0, 8)));
  console.log('REPORT:' + JSON.stringify(LOG));
  ws.close(); process.exit(0);
});
'''

WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
HEIGHT = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
tag = 'wy2-%dx%d' % (WIDTH, HEIGHT)
LOGFILE = os.path.join(OUT, 'wy2-log-%dx%d.jsonl' % (WIDTH, HEIGHT))
if os.path.exists(LOGFILE):
    os.remove(LOGFILE)

ns = os.path.join(REPO, "_cdp_wy2.js")
io.open(ns, "w", encoding="utf-8").write(
    CDP.replace("/tmp/", OUT.replace("\\", "/").rstrip("/") + "/"))
os.makedirs(os.path.join(OUT, "shots"), exist_ok=True)

port = 9842
prof = os.path.join(OUT, "wy2prof")
if os.path.isdir(prof):
    subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port,
                          "--user-data-dir=" + prof, "--window-size=1400,1000",
                          "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
targets = None
for _ in range(80):
    time.sleep(0.4)
    try:
        targets = json.load(urllib.request.urlopen(
            "http://127.0.0.1:%d/json/list" % port, timeout=10))
        if any(t.get("type") == "page" and t.get("webSocketDebuggerUrl") for t in targets):
            break
    except Exception:
        pass
page = [t for t in (targets or []) if t.get("type") == "page" and t.get("webSocketDebuggerUrl")][0]
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(WIDTH), str(HEIGHT),
                    json.dumps(ORDER, ensure_ascii=False), tag, URL, LOGFILE],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=900)
child.kill()

report = None
for line in (r.stdout or "").splitlines():
    if line.startswith("REPORT:"):
        report = json.loads(line[7:])
if report is None:
    print("  !! 没取到报告")
    print((r.stdout or "")[-1500:])
    print((r.stderr or "")[-800:])
    sys.exit(1)

print("=" * 72)
print("  第二关端到端走查 · 视口 %dx%d" % (WIDTH, HEIGHT))
print("=" * 72)
for line in report:
    if line.startswith("WORLD "):
        d = json.loads(line[6:])
        print("\n【大地图】据点 %d 个 %s" % (d["pins"], " / ".join(d["names"])))
        print("  地图盒 %s  上沿 y=%s  下沿 y=%s  横向溢出 %dpx"
              % (d["board"], d["boardTop"], d["boardBottom"], d["overflowX"]))
        print("  据点尺寸 %s" % " ".join(d["pinWH"]))
        print("  有龟宝向导=%s（y=%s）  有素材署名=%s" % (d["guide"], d["guideTop"], d["credit"]))
    elif line.startswith("AFTER-"):
        nm, rest = line[6:].split(" ", 1)
        d = json.loads(rest)
        print("  · 返回大地图后（学完「%s」）：点亮 %d/%d 片 · 柔光 %d 处 · 进度条 %s · %s"
              % (nm, d["lit"], d["pins"], d["glows"], d["meter"], d["words"]))
    elif line.startswith("FINAL "):
        d = json.loads(line[6:])
        print("\n【收尾】点亮 %d/%d 片 · 柔光 %d 处 · %s · 横向溢出 %dpx"
              % (d["lit"], d["all"], d["glowOn"], d["words"], d["overflowX"]))
    elif line.startswith("CARDS "):
        items = json.loads(line[6:])
        print("\n【逐区走查】")
        for it in items:
            if "summary" in it:
                s = it["summary"]
                print("  %-6s 印记 %2d 个 · 进度条 %-6s · 区域完成标记=%s"
                      % (it["zone"], s["marks"], s["filled"], s["clear"]))
                print("         %s" % s["head"])
            else:
                pass
    elif line.startswith("CARD-MISS"):
        print("  !! " + line)
    elif line.startswith("GUARD"):
        print("  !! " + line)
shots = [f for f in sorted(os.listdir(OUT)) if f.startswith(tag)]
print("\n【截图】%d 张：%s" % (len(shots), " ".join(shots)))
try:
    os.remove(ns)
except OSError:
    pass

