# -*- coding: utf-8 -*-
"""演示模式：进入 → 校验进度被填满 → 退出 → 校验逐键还原。"""
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
  .then(r => { if (r && r.exceptionDetails) return 'EXC:' +
    ((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || '?');
    return (r.result && r.result.value); });
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: URL});
  await sleep(6000);
  const probe = "JSON.stringify({panel:!!document.querySelector('.sect h4') ," +
    "hasDemo:!(typeof App.demo==='undefined'),active:App.demo?App.demo.active():null," +
    "btn:(function(){var b=[].slice.call(document.querySelectorAll('button'))" +
    ".filter(function(x){return /演示/.test(x.textContent)})[0];return b?b.textContent:'none';})()," +
    "wy:(App.store.get('wangyi',null)||{}).done?Object.keys(App.store.get('wangyi',{}).done).length:0," +
    "boss:((App.store.get('bossraid',{})||{}).cleared||[]).length," +
    "bb:((App.store.get('bonebuild',{})||{}).done||[]).length})";
  console.log('BEFORE ' + await ev(probe));

  console.log('ENTER ' + await ev("(function(){var r=App.demo.enter();" +
    "return JSON.stringify(r);})()"));
  await sleep(400);
  console.log('AFTER ' + await ev(probe));

  /* 顶栏印章是否出现 */
  console.log('SEAL ' + await ev("(function(){var s=document.querySelector('.demo-seal');" +
    "return s?s.textContent:'none';})()"));

  /* 图鉴解锁数：进图鉴页读头部的 "N / 102" */
  await ev("location.hash='#/atlas'");
  await sleep(2500);
  console.log('ATLAS ' + await ev("(function(){var t=document.body.innerText;" +
    "var m=t.match(/(\\d+)\\s*\\/\\s*(\\d+)\\s*已解锁/);return m?m[0]:'n/a';})()"));

  /* 退出并还原 */
  console.log('EXIT ' + await ev("(function(){return App.demo.exit();})()"));
  await sleep(300);
  console.log('RESTORED ' + await ev(probe));
  const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(OUTDIR + '/demo-settings.png', Buffer.from(s.data, 'base64'));
  ws.close(); process.exit(0);
});
'''

js_path = os.path.join(OUT, "_probe_demo.js")
io.open(js_path, "w", encoding="utf-8").write(JS)
port = 9898
prof = os.path.join(OUT, "demoprof")
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
    for tag in ("BEFORE", "ENTER", "AFTER", "SEAL", "ATLAS", "EXIT", "RESTORED"):
        if line.startswith(tag + " "):
            print("  %-9s %s" % (tag, line[len(tag) + 1:]))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
try:
    os.remove(js_path)
except OSError:
    pass
