# -*- coding: utf-8 -*-
"""排查：为什么进入演示后顶栏没有「演示中」印章。"""
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
const URL = process.argv[3];
let id = 0; const pend = new Map();
const send = (m, q) => new Promise(r => { const i = ++id; pend.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: q || {}})); });
ws.addEventListener('message', e => { const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); } });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = x => send('Runtime.evaluate', {expression: x, returnByValue: true})
  .then(r => (r && r.exceptionDetails)
    ? 'EXC:' + ((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || '?')
    : (r.result && r.result.value));
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: URL});
  await sleep(6000);
  console.log('API ' + await ev(
    "JSON.stringify({renderHeader:typeof App.renderHeader,go:typeof App.go," +
    "route:typeof App.route,sealEl:!!document.querySelector('.top-seal')," +
    "siteTop:!!document.getElementById('siteTop')})"));
  console.log('ENTER ' + await ev("(function(){try{var r=App.demo.enter();" +
    "App.renderHeader&&App.renderHeader();" +
    "return JSON.stringify({r:r,seal:!!document.querySelector('.demo-seal')," +
    "right:(document.querySelector('.top-right')||{}).innerHTML?document.querySelector('.top-right').innerHTML.slice(0,200):'no-right'});}" +
    "catch(e){return 'THROW:'+e.message;}})()"));
  ws.close(); process.exit(0);
});
'''
js_path = os.path.join(OUT, "_probe_demo3.js")
io.open(js_path, "w", encoding="utf-8").write(JS)
port = 9900
prof = os.path.join(OUT, "demoprof3")
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
r = subprocess.run([NODE, js_path, page["webSocketDebuggerUrl"], URL],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=200)
child.kill()
for line in (r.stdout or "").splitlines():
    for tag in ("API", "ENTER"):
        if line.startswith(tag + " "):
            print("  %-6s %s" % (tag, line[len(tag) + 1:][:400]))
if r.stderr:
    print("  stderr: " + r.stderr[:200])
try:
    os.remove(js_path)
except OSError:
    pass
