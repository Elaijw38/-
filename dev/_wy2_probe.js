/* 字趣 · 第二关（殷商王邑）浏览器内验收探针 —— 开发自查，不参与部署。

用法：
  node dev/_wy2_probe.js <url> <W> <H> <tag> [zoneIndex]

做四件事：
  1) 进 #/play/wangyi-map → 点第 zoneIndex 个区域入口 → 量「全景是否整幅铺满」
  2) 点「+」放大 → 在目标热点位置派发 pointer 事件 → 断言弹出的字卡字符正确
  3) 点「按区域看」的某个区域 → 断言滚动位置落在该区域
  4) 截图（整页 + 视口）

硬约束（前几轮踩过的）：
  · SVG 无 .click()，热点一律派发 pointerdown/pointerup（代码认的是 pointerup）。
  · setZoom 会整屏重画，动作前必须重新查询节点。
  · headless 窗口有最小尺寸，必须走 CDP Emulation 覆盖。
*/
const { spawn } = require('child_process');
const http = require('http');
const path = require('path'), os = require('os'), fs = require('fs');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const URL_ARG = process.argv[2] || 'http://127.0.0.1:8099/index.html';
const W = parseInt(process.argv[3] || '390', 10);
const H = parseInt(process.argv[4] || '780', 10);
const TAG = process.argv[5] || 'probe';
const ZONE_IX = parseInt(process.argv[6] || '4', 10);
const PORT = 9400 + (W % 300);
const OUT = path.join(__dirname, '..', 'out', 'wy2-probe');
fs.mkdirSync(OUT, { recursive: true });

const profile = path.join(os.tmpdir(), 'zq_wy2_' + TAG + '_' + W);
fs.rmSync(profile, { recursive: true, force: true });

function getJson(u) {
  return new Promise((res, rej) => {
    http.get(u, r => { let s = ''; r.on('data', c => s += c); r.on('end', () => { try { res(JSON.parse(s)); } catch (e) { rej(e); } }); }).on('error', rej);
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
const L = [];
const say = s => { L.push(s); console.log(s); };

(async () => {
  const child = spawn(EDGE, [
    '--headless=new', '--disable-gpu', '--no-sandbox',
    '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + profile,
    '--window-size=1200,900',
    'about:blank',
  ], { stdio: 'ignore' });

  let targets = null;
  for (let i = 0; i < 60; i++) {
    await sleep(400);
    try {
      targets = await getJson('http://127.0.0.1:' + PORT + '/json/list');
      if (targets && targets.some(t => t.type === 'page' && t.webSocketDebuggerUrl)) break;
    } catch (e) { /* 还没起来 */ }
  }
  const page = (targets || []).find(t => t.type === 'page' && t.webSocketDebuggerUrl);
  if (!page) { console.log('拿不到调试目标'); child.kill(); process.exit(1); }

  /* Node 22 自带全局 WebSocket，不再依赖 ws 包（工作区里没有装） */
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const send = (method, params) => new Promise(res => {
    const myId = ++id;
    pending.set(myId, res);
    ws.send(JSON.stringify({ id: myId, method, params: params || {} }));
  });
  const logs = [];
  ws.addEventListener('message', evt => {
    const msg = JSON.parse(String(evt.data));
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); return; }
    if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
      logs.push((msg.params.args || []).map(a => a.value || a.description || '').join(' '));
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails || {};
      logs.push('EXC ' + ((d.exception && (d.exception.description || d.exception.value)) || d.text));
    }
  });
  await new Promise(r => ws.addEventListener('open', r));
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: W, height: H, deviceScaleFactor: 1, mobile: W < 700,
  });

  const ev = async (expr) => {
    const r = await send('Runtime.evaluate', {
      expression: '(function(){try{return JSON.stringify(' + expr + ')}catch(e){return JSON.stringify({err:String(e)})}})()',
      returnByValue: true, awaitPromise: false,
    });
    if (!r || !r.result) return { err: 'no result' };
    try { return JSON.parse(r.result.value); } catch (e) { return { err: String(r.result.value) }; }
  };
  const shot = async (name) => {
    const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    if (!r || !r.data) { say('  截图失败 ' + name); return; }
    fs.writeFileSync(path.join(OUT, name + '.png'), Buffer.from(r.data, 'base64'));
    say('  截图 ' + path.join('out/wy2-probe', name + '.png'));
  };

  say('=== 第二关验收 ' + TAG + '  视口 ' + W + '×' + H + ' ===');
  await send('Page.navigate', { url: URL_ARG + '#/play/wangyi-map' });
  for (let i = 0; i < 40; i++) {
    await sleep(400);
    const ok = await ev("!!document.querySelector('.wy2-pin')");
    if (ok === true) break;
  }

  const world = await ev("(function(){var a=document.querySelectorAll('.wy2-pin');" +
    "return {pins:a.length, names:[].map.call(a,function(e){var b=e.querySelector('b');return b?b.textContent:''})}})()");
  say('大地图入口：' + JSON.stringify(world));
  await shot(TAG + '-0-world');

  /* 进入指定区域 */
  const enter = await ev("(function(){var a=document.querySelectorAll('.wy2-pin');" +
    "var e=a[" + ZONE_IX + "]; if(!e) return {ok:false}; e.click(); return {ok:true}})()");
  say('进入第 ' + (ZONE_IX + 1) + ' 个区域：' + JSON.stringify(enter));
  for (let i = 0; i < 30; i++) {
    await sleep(300);
    const ok = await ev("!!document.querySelector('.wy2-viewport svg.wy2-hotspots')");
    if (ok === true) break;
  }
  await sleep(900);

  /* --- 1) 全景是否整幅铺满（contain），且整幅都落在**首屏可见范围**内 --- */
  const fit = await ev(`(function(){
    var vp=document.querySelector('.wy2-viewport'), st=document.querySelector('.wy2-stage');
    if(!vp||!st) return {err:'缺节点'};
    var v=vp.getBoundingClientRect(), s=st.getBoundingClientRect();
    var sp=document.querySelectorAll('.wy2-spot').length;
    var ih=window.innerHeight||0, sy=window.pageYOffset||0;
    var hd=document.querySelector('header.top, .top');
    var headH=hd?Math.round(hd.getBoundingClientRect().height):0;
    /* 地图（stage）在窗口坐标里的上下边 */
    var mapTop=Math.round(s.top), mapBot=Math.round(s.bottom);
    var barTop=Math.round(document.querySelector('.wy2-zone-top').getBoundingClientRect().top);
    var tools=document.querySelector('.wy2-tools');
    var tb=tools?tools.getBoundingClientRect():null;
    return { vw:Math.round(v.width), vh:Math.round(v.height),
             sw:Math.round(s.width), sh:Math.round(s.height),
             spots:sp, zoom:window.__wyDbg.state().zoom,
             fitsW:s.width<=v.width+1.5, fitsH:s.height<=v.height+1.5,
             ovfX:Math.round(vp.scrollWidth-vp.clientWidth), ovfY:Math.round(vp.scrollHeight-vp.clientHeight),
             headH:headH, barTop:barTop,
             toolsVisible: tb ? (tb.top>=headH-1 && tb.bottom<=ih) : null,
             vpTop:Math.round(v.top), vpBot:Math.round(v.bottom), screenH:ih, pageY:Math.round(sy),
             mapOnScreen: mapTop>=headH-1 && mapBot<=ih };   /* 不钻到固定顶栏下面，也不出屏 */
  })()`);
  say('① 全景：' + JSON.stringify(fit));
  say('   判定 ' + (fit.fitsW && fit.fitsH ? 'PASS 整幅完整显示' : 'FAIL 有裁剪')
    + ' / ' + (fit.mapOnScreen ? '首屏可见' : 'FAIL 整幅落在首屏之外')
    + ' / ' + (fit.toolsVisible ? '工具条可见' : 'FAIL 工具条被顶栏遮住'));
  const span = await ev("(function(){var a=document.querySelectorAll('.wy2-region');" +
    "return {n:a.length, names:[].map.call(a,function(e){return e.textContent})}})()");
  say('   区域按钮：' + JSON.stringify(span));
  const gh = await ev("(function(){var e=document.querySelector('.wy2-gesture');" +
    "return e?{vis:getComputedStyle(e).opacity, txt:e.textContent.slice(0,60)}:null})()");
  say('   手势提示：' + JSON.stringify(gh));
  await shot(TAG + '-1-panorama');

  /* --- 2) 放大后点热点 → 字卡 --- */
  /* 把目标热点滚到视口中央（真人会先拖过去），再派发 pointer 事件 */
  const place = async (ch) => ev(`(function(){
    var o=App.levels.map.zones[${ZONE_IX}], oo=null;
    for(var i=0;i<o.objects.length;i++){ if(o.objects[i].char==='${ch}') oo=o.objects[i]; }
    if(!oo) return {err:'无此字', chars:o.objects.map(function(q){return q.char})};
    var vp=document.querySelector('.wy2-viewport');
    var st=document.querySelector('.wy2-stage');
    var s=st.offsetWidth/2624;
    vp.scrollLeft=Math.max(0, oo.x*s - vp.clientWidth/2);
    vp.scrollTop=Math.max(0, oo.y*s - vp.clientHeight/2);
    return {ok:true, s:s};
  })()`);
  const posOf = async (ch) => ev(`(function(){
    var o=App.levels.map.zones[${ZONE_IX}], oo=null;
    for(var i=0;i<o.objects.length;i++){ if(o.objects[i].char==='${ch}') oo=o.objects[i]; }
    if(!oo) return {err:'无此字'};
    var vp=document.querySelector('.wy2-viewport');
    var svg=vp.querySelector('svg.wy2-hotspots');
    var r=svg.getBoundingClientRect(), vr=vp.getBoundingClientRect();
    var sc=Math.min(r.width/2624, r.height/1472);
    var offX=r.left+(r.width-2624*sc)/2, offY=r.top+(r.height-1472*sc)/2;
    var x=offX+oo.x*sc, y=offY+oo.y*sc;
    return {x:x, y:y, sc:sc,
            onScreen: x>vr.left+8 && x<vr.right-8 && y>vr.top+8 && y<vr.bottom-8};
  })()`);
  const tapXY = async (p, tapN) => {
    if (!p || p.err || p.onScreen === false) return false;
    await ev(`(function(){
      var vp=document.querySelector('.wy2-viewport');
      var o={clientX:${p.x}, clientY:${p.y}, bubbles:true, cancelable:true,
             pointerId:${tapN || 1}, pointerType:'touch', isPrimary:true};
      vp.dispatchEvent(new PointerEvent('pointerdown', o));
      vp.dispatchEvent(new PointerEvent('pointerup', o));
      return true;
    })()`);
    return true;
  };
  const cardInfo = () => ev("(function(){var c=document.querySelector('.wy2-card');" +
    "if(!c) return {open:false}; var ch=c.querySelector('.wy2-card-char')," +
    " m=c.querySelector('.wy2-card-mean');" +
    "return {open:true, char:ch?ch.textContent:'', mean:m?m.textContent:''}})()");

  const target = process.env.WY2_TAP_CHAR || '虎';
  const zoomIn = `(function(){var b=document.querySelector('[aria-label="放大"]');if(!b)return false;b.click();return true})()`;

  /* --- 2) 全景态点热点：应先放大、不开卡 --- */
  await place(target);
  const p1 = await posOf(target);
  const t1 = await tapXY(p1, 1);
  await sleep(900);
  const a1 = await ev("(function(){return {s:window.__wyDbg.state(), card:!!document.querySelector('.wy2-card')}})()");
  say('② 全景态点「' + target + '」：' + JSON.stringify(p1));
  say('   tap=' + t1 + ' → ' + JSON.stringify(a1));
  say('   判定 ' + (t1 && !a1.card && a1.s.zoom > 1 && a1.s.lens === target
      ? 'PASS 先放大到该字，未直接开卡' : 'FAIL 行为不符'));
  await shot(TAG + '-2-zoomto');

  /* --- 3) 再点同一处：开卡，且字正确 --- */
  await place(target);
  const p2 = await posOf(target);
  const t2 = await tapXY(p2, 2);
  await sleep(900);
  const c2 = await cardInfo();
  say('③ 放大后再点同一处：' + JSON.stringify(p2));
  say('   ' + JSON.stringify(c2));
  say('   判定 ' + (t2 && c2.open && c2.char === target
      ? 'PASS 命中「' + target + '」' : 'FAIL 期望「' + target + '」'));
  await shot(TAG + '-3-card');

  /* 关掉卡片，并标记为已学（看完成标记长什么样） */
  await ev("(function(){var x=document.querySelector('.wy2-card-x');if(x)x.click();return true})()");
  await sleep(400);
  const doneShot = await ev(`(function(){
    var ch='${target}';
    var st=App.store.get('wangyi',{}); if(!st.done) st.done={};
    var zid=App.levels.map.zones[${ZONE_IX}].id;
    st.done[zid]=st.done[zid]||[]; if(st.done[zid].indexOf(ch)<0) st.done[zid].push(ch);
    App.store.set('wangyi', st);
    return {zid:zid, done:st.done[zid]};
  })()`);
  say('   写入已学记录：' + JSON.stringify(doneShot));
  await ev("(function(){var b=document.querySelectorAll('.wy2-tool')[1];if(b)b.click();return true})()");
  await sleep(800);
  const seal = await ev("(function(){var s=document.querySelector('.wy2-seal');" +
    "if(!s) return {seal:false}; var r=s.querySelector('circle'), t=s.querySelector('text');" +
    "var rb=r.getBoundingClientRect();" +
    "return {seal:true, char:t?t.textContent:'', rp:Math.round(rb.width/2), fill:getComputedStyle(r).fill}})()");
  say('   已学印记（开着"标出可点处"）：' + JSON.stringify(seal));
  await shot(TAG + '-4-done-seal');

  /* --- 4) 按区域看 --- */
  const reg = await ev("(function(){var a=document.querySelectorAll('.wy2-region');if(a.length<2)return {ok:false};" +
    "a[1].click();return {ok:true,name:a[1].textContent}})()");
  await sleep(900);
  const rc = await ev("(function(){var vp=document.querySelector('.wy2-viewport');var s=window.__wyDbg.state();" +
    "return {zoom:s.zoom, region:s.region, sl:Math.round(vp.scrollLeft), st:Math.round(vp.scrollTop)," +
    "ovfX:Math.round(vp.scrollWidth-vp.clientWidth), ovfY:Math.round(vp.scrollHeight-vp.clientHeight)}})()");
  say('④ 区域切换 ' + JSON.stringify(reg) + ' → ' + JSON.stringify(rc));
  say('   判定 ' + (reg.ok && rc.zoom > 1 && (rc.ovfX > 0 || rc.ovfY > 0)
      ? 'PASS 已放大到该区域且可拖动' : 'FAIL'));
  await shot(TAG + '-5-region');

  const minus = await ev("(function(){var b=document.querySelector('[aria-label=\"缩小\"]');" +
    "if(!b)return false;b.click();return true})()");
  await sleep(800);
  const back = await ev("(function(){var vp=document.querySelector('.wy2-viewport');" +
    "return {zoom:window.__wyDbg.state().zoom, sw:Math.round(document.querySelector('.wy2-stage').getBoundingClientRect().width), vw:Math.round(vp.getBoundingClientRect().width)}})()");
  say('   点「−」回退：' + JSON.stringify(back) + '（minus=' + minus + '）');
  await shot(TAG + '-6-zoomout');

  say('控制台错误：' + (logs.length ? JSON.stringify(logs.slice(0, 4)) : '无'));
  say('=== 完 ===');

  ws.close(); child.kill();
  await sleep(300);
  fs.rmSync(profile, { recursive: true, force: true });
  process.exit(0);
})().catch(e => { console.log('出错: ' + (e && e.stack || e)); process.exit(1); });
