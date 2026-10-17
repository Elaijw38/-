# -*- coding: utf-8 -*-
"""截图：第三关里「有专属形象」与「无专属形象」两种关卡的差别。

做法：打开选关页，把指针移到一个关卡珠上（触发 showArtOf 换形象），
各截一张：焚（有形象，映射到火怪）与 涉（无形象，回落到本阶徽记）。
"""
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
URL = "http://127.0.0.1:8099/index.html#/play/boss-raid"

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
  .then(r => (r && r.exceptionDetails)
    ? 'EXC:' + (r.exceptionDetails.exception.description || '?')
    : (r.result && r.result.value));
const shot = async n => { const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(OUTDIR + '/' + n, Buffer.from(s.data, 'base64')); };

const HOVER = ch => "(function(){var all=[].slice.call(document.querySelectorAll('.bo-bead'));" +
  "var i=%CH%; if(!all[i]) return 'no-bead:'+all.length;" +
  "all[i].dispatchEvent(new PointerEvent('pointerenter',{bubbles:true}));" +
  "all[i].focus(); return 'ok';})()";

ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: URL});
  await sleep(7000);
  console.log('PAGE ' + await ev("document.querySelectorAll('.bo-tier').length"));
  await ev("App.demo.enter();App.shell.renderHeader();App.router.render();");
  await sleep(2500);
  for (const [ch, name] of [[2, 'shot-with-art.png'], [0, 'shot-no-art.png']]) {
    const js = HOVER(ch).replace('%CH%', JSON.stringify(ch));
    console.log('HOVER' + ch + ' ' + await ev(js));
    await sleep(900);
    console.log('IMG' + ch + ' ' + await ev("(function(){var i=document.querySelector('.bo-tier-art img');" +
      "if(i) return 'IMG '+(i.getAttribute('src')||'');var art=document.querySelector('.bo-tier-art');var nm=art.querySelector('.bo-tier-artname');return 'artHTML='+art.innerHTML.slice(0,120)+' | name='+(nm?nm.textContent:'?');})()"));
    await shot(name);
  }
  ws.close(); process.exit(0);
});
'''
js_path = os.path.join(OUT, "_probe_shot.js")
io.open(js_path, "w", encoding="utf-8").write(JS)
port = 9902
prof = os.path.join(OUT, "shotprof")
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
    if line.startswith(("PAGE ", "HOVER", "IMG")):
        print("  " + line[:120])
if r.stderr:
    print("  stderr: " + r.stderr[:200])
try:
    os.remove(js_path)
except OSError:
    pass
