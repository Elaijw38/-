# -*- coding: utf-8 -*-
"""走真实 UI 路径：设置页点「进入演示模式」→ 顶栏应出现「演示中」印章 → 点印章退出并还原。"""
import io
import json
import os
import subprocess
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")
URL = "http://127.0.0.1:8099/index.html#/settings"

JS = r'''
const ws = new WebSocket(process.argv[2]);
const OUTDIR = process.argv[3], URL = process.argv[4];
let id = 0; const pend = new Map();
const send = (m, q) => new Promise(r => { const i = ++id; pend.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: q || {}})); });
ws.addEventListener('message', e => { const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); } });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = x => send('Runtime.evaluate', {expression: x, returnByValue: true})
  .then(r => (r && r.exceptionDetails) ? 'EXC:' + (r.exceptionDetails.exception.description||'?')
    : (r.result && r.result.value));
const shot = async n => { const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(OUTDIR + '/' + n, Buffer.from(s.data, 'base64')); };
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: URL});
  await sleep(6000);
  console.log('CLICK ' + await ev("(function(){var b=[].slice.call(document.querySelectorAll('button'))" +
    ".filter(function(x){return x.textContent.indexOf('进入演示')>=0})[0];" +
    "if(!b)return 'no-btn';b.click();return 'ok';})()"));
  await sleep(2500);
  console.log('SEAL ' + await ev("(function(){var s=document.querySelector('.demo-seal');" +
    "return s?(s.textContent+'/'+s.tagName):'none';})()"));
  console.log('STATE ' + await ev("JSON.stringify({active:App.demo.active()," +
    "wy:Object.keys((App.store.get('wangyi',{})||{}).done||{}).length," +
    "boss:((App.store.get('bossraid',{})||{}).cleared||[]).length," +
    "panelText:(document.querySelector('.sect:last-child h4')||{}).textContent||''})"));
  await shot('demo-on.png');
  console.log('EXITSEAL ' + await ev("(function(){var s=document.querySelector('.demo-seal');" +
    "if(!s)return 'no-seal';s.click();return 'clicked';})()"));
  await sleep(2000);
  console.log('AFTER ' + await ev("JSON.stringify({active:App.demo.active()," +
    "wy:Object.keys((App.store.get('wangyi',{})||{}).done||{}).length," +
    "boss:((App.store.get('bossraid',{})||{}).cleared||[]).length," +
    "seal:!!document.querySelector('.demo-seal')})"));
  await shot('demo-off.png');
  ws.close(); process.exit(0);
});
'''
js_path = os.path.join(OUT, "_probe_demo2.js")
io.open(js_path, "w", encoding="utf-8").write(JS)
port = 9899
prof = os.path.join(OUT, "demoprof2")
if os.path.isdir(prof):
    subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port,
                          "--user-data-dir=" + prof, "--window-size=1500,1000",
                          "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
targets = None
for _ in range(80):
    time.sleep(0.4)
    try:
        targets = json.load(urllib.request.urlopen(
            "http://127.0.0.1:%d/json/list" % port, timeout=8))
        if any(t.get("type") == "page" and t.get("webSocketDebuggerUrl") for t in targets):
            break
    except Exception:
        pass
page = [t for t in (targets or []) if t.get("type") == "page"
        and t.get("webSocketDebuggerUrl")][0]
r = subprocess.run([NODE, js_path, page["webSocketDebuggerUrl"], OUT, URL],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=240)
child.kill()
for line in (r.stdout or "").splitlines():
    for tag in ("CLICK", "SEAL", "STATE", "EXITSEAL", "AFTER"):
        if line.startswith(tag + " "):
            print("  %-9s %s" % (tag, line[len(tag) + 1:]))
if r.stderr:
    print("  stderr: " + r.stderr[:200])
try:
    os.remove(js_path)
except OSError:
    pass
