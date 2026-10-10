// 用 CDP 精确设置视口后量几何（headless 窗口宽度有下限，必须走 CDP 才能得到真实手机宽度）
const { spawn } = require('child_process');
const http = require('http');
const path = require('path'), os = require('os'), fs = require('fs');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const URL_ARG = process.argv[2];
const W = parseInt(process.argv[3] || '390', 10);
const H = parseInt(process.argv[4] || '780', 10);
const PORT = 9333 + (W % 100);

const profile = path.join(os.tmpdir(), 'zq_cdp_' + W);
fs.rmSync(profile, { recursive: true, force: true });

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let s = '';
      res.on('data', c => s += c);
      res.on('end', () => { try { resolve(JSON.parse(s)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const child = spawn(EDGE, [
    '--headless=new', '--disable-gpu', '--no-sandbox',
    '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + profile,
    '--window-size=1200,900',
    URL_ARG,
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

  const WebSocket = require('ws');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const send = (method, params) => new Promise(res => {
    const myId = ++id;
    pending.set(myId, res);
    ws.send(JSON.stringify({ id: myId, method, params: params || {} }));
  });
  ws.on('message', raw => {
    const msg = JSON.parse(raw.toString());
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); }
  });

  await new Promise(r => ws.on('open', r));
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: W, height: H, deviceScaleFactor: 1, mobile: true,
  });
  await send('Page.navigate', { url: URL_ARG });
  await sleep(3500);

  const expr = `(function(){
    function rect(sel){
      var el=document.querySelector(sel);
      if(!el) return '不存在';
      var r=el.getBoundingClientRect(), cs=getComputedStyle(el);
      return 'left='+Math.round(r.left)+' w='+Math.round(r.width)+' display='+cs.display+' pos='+cs.position+' dir='+cs.flexDirection;
    }
    return JSON.stringify({
      vw: innerWidth,
      nav: document.body.getAttribute('data-nav'),
      navEl: rect('.app-nav'), brand: rect('.app-nav .nav-brand'),
      sub: rect('.app-nav .nav-sub'), item1: rect('.app-nav .nav-item'),
      item4: rect('.app-nav .nav-item:nth-of-type(4)'), foot: rect('.app-nav .nav-foot'),
      wrap: rect('.wrap'), modeCard: rect('.mode-card'), modeGrid: rect('.mode-grid'),
      main: rect('.app-main'), shell: rect('.app-shell'),
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth
    });
  })()`;
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  const o = JSON.parse(r.result.value);

  console.log('视口 ' + o.vw + 'px   body[data-nav]=' + o.nav);
  console.log('  文档 scrollW=' + o.scrollW + '  clientW=' + o.clientW +
    (o.scrollW > o.clientW ? '   <-- 横向溢出 ' + (o.scrollW - o.clientW) + 'px' : '   无横向溢出'));
  for (const k of ['shell', 'main', 'navEl', 'brand', 'sub', 'item1', 'item4', 'foot', 'wrap', 'modeGrid', 'modeCard']) {
    console.log('  ' + k.padEnd(9) + ' ' + o[k]);
  }
  ws.close(); child.kill();
  await sleep(300);
  fs.rmSync(profile, { recursive: true, force: true });
  process.exit(0);
})().catch(e => { console.log('出错: ' + e.message); process.exit(1); });
