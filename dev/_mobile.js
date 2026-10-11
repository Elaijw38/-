/* 移动端实际审计：用 CDP 精确设置设备视口后测量并截图。
   必须走 CDP —— Edge 无头窗口有最小宽度（实测 482px），
   用 --window-size 量不出 390px 手机上的真实布局。

   用法：node dev/_mobile.js <url> [宽] [高] [截图输出路径]
   输出：视口、是否横向溢出、超出右缘的元素清单、截图。 */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path'), os = require('os'), fs = require('fs');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const URL_ARG = process.argv[2];
const W = parseInt(process.argv[3] || '390', 10);
const H = parseInt(process.argv[4] || '844', 10);
const SHOT = process.argv[5] || '';
const PORT = 9400 + (W % 100);
const profile = path.join(os.tmpdir(), 'zq_m_' + W);

if (!URL_ARG) { console.log('用法: node dev/_mobile.js <url> [宽] [高] [截图路径]'); process.exit(1); }
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

const AUDIT = `(function(){
  var vw = document.documentElement.clientWidth;
  var rows = [];
  document.querySelectorAll('body *').forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (r.right - vw > 1) {
      var cls = (el.className && el.className.baseVal !== undefined)
        ? el.className.baseVal : (el.className || '');
      var txt = (el.textContent || '').trim().slice(0, 14);
      rows.push([Math.round(r.right - vw),
        el.tagName.toLowerCase() + (cls ? '.' + String(cls).trim().split(/\\s+/).join('.') : ''),
        Math.round(r.left), Math.round(r.width), txt]);
    }
  });
  rows.sort(function (a, b) { return b[0] - a[0]; });
  return JSON.stringify({
    vw: vw,
    clientW: document.documentElement.clientWidth,
    scrollW: document.documentElement.scrollWidth,
    bodyW: document.body.scrollWidth,
    over: rows.slice(0, 12),
    navOn: (function () { var a = document.querySelector('.top-link.on'); return a ? a.textContent : '（无）'; })(),
    topH: (function () { var t = document.querySelector('.top'); return t ? Math.round(t.getBoundingClientRect().height) : -1; })(),
    footH: (function () { var f = document.querySelector('.footer'); return f ? Math.round(f.getBoundingClientRect().height) : -1; })(),
    smallTaps: (function () {
      var n = 0, list = [];
      document.querySelectorAll('a, button, .btn, .chipbtn, .atlas-card, .play-card').forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        if (r.height < 32 || r.width < 32) {
          n++;
          if (list.length < 6) {
            list.push(((el.textContent || '').trim().slice(0, 10) || el.tagName) +
              '(' + Math.round(r.width) + 'x' + Math.round(r.height) + ')');
          }
        }
      });
      return { n: n, list: list };
    })()
  });
})()`;

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

  /* WebSocket 客户端：优先用 Node 自带的全局 WebSocket（Node 22+ 稳定提供），
     没有才退回 require('ws')。项目里没有装 ws，所以实际走的是前者。 */
  let WS;
  if (typeof WebSocket === 'function') {
    WS = WebSocket;
  } else {
    try { WS = require('ws'); }
    catch (e) { console.log('本机没有可用的 WebSocket 实现，无法走 CDP'); child.kill(); process.exit(1); }
  }
  const ws = new WS(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const onMsg = raw => {
    const text = (raw && raw.data !== undefined) ? raw.data : raw;
    const msg = JSON.parse(String(text));
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); }
  };
  if (typeof ws.addEventListener === 'function') { ws.addEventListener('message', onMsg); }
  else { ws.on('message', onMsg); }
  const send = (method, params) => new Promise(res => {
    const myId = ++id;
    pending.set(myId, res);
    ws.send(JSON.stringify({ id: myId, method, params: params || {} }));
  });
  const closeWs = () => { try { ws.close(); } catch (e) {} };

  await new Promise(r => {
    if (typeof ws.addEventListener === 'function') { ws.addEventListener('open', r); }
    else { ws.on('open', r); }
  });
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: W, height: H, deviceScaleFactor: 1, mobile: true,
  });
  await send('Page.navigate', { url: URL_ARG });
  await sleep(4000);

  const r = await send('Runtime.evaluate', { expression: AUDIT, returnByValue: true });
  let o;
  try { o = JSON.parse(r.result.value); }
  catch (e) { console.log('审计脚本执行失败: ' + (r.result && r.result.description || e.message)); closeWs(); child.kill(); process.exit(1); }

  console.log('  视口 ' + o.vw + 'px　顶栏高 ' + o.topH + '　页脚高 ' + o.footH
    + '　当前导航项「' + o.navOn + '」');
  console.log('  文档 scrollWidth=' + o.scrollW + '  clientWidth=' + o.clientW
    + (o.scrollW > o.clientW ? '   ← 横向溢出 ' + (o.scrollW - o.clientW) + 'px' : '   无横向溢出 ✓'));
  if (o.over.length) {
    console.log('  超出右缘的元素：');
    o.over.forEach(function (x) {
      console.log('    +' + x[0] + 'px  ' + x[1] + '  left=' + x[2] + ' w=' + x[3]
        + (x[4] ? '  「' + x[4] + '」' : ''));
    });
  } else {
    console.log('  无元素超出右缘 ✓');
  }
  if (o.smallTaps.n) {
    console.log('  触控目标偏小（<' + 32 + 'px）: ' + o.smallTaps.n + ' 个  '
      + o.smallTaps.list.join('、'));
  } else {
    console.log('  触控目标尺寸合格 ✓');
  }

  if (SHOT) {
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
    if (shot && shot.data) {
      fs.writeFileSync(SHOT, Buffer.from(shot.data, 'base64'));
      console.log('  截图 ' + SHOT + '  ' + fs.statSync(SHOT).size + 'B');
    }
  }

  closeWs(); child.kill();
  await sleep(300);
  fs.rmSync(profile, { recursive: true, force: true });
  process.exit(0);
})().catch(e => { console.log('出错: ' + e.message); process.exit(1); });
