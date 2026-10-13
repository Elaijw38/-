# -*- coding: utf-8 -*-
"""量一下第二关小地图视口的真实高度，确认 CSS 有没有生效、图有没有被顶栏压住。"""
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

CDP = r'''
const ws = new WebSocket(process.argv[2]);
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
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: process.argv[3]});
  await sleep(6000);
  await ev("(function(){var p=[].slice.call(document.querySelectorAll('.wy2-pin'))" +
    ".filter(function(e){return e.querySelector('b').textContent==='人居器物';})[0];" +
    "if(p) p.click();})()");
  await sleep(1400);
  const out = await ev("(function(){" +
    "var vp=document.querySelector('.wy2-viewport');" +
    "var top=document.querySelector('.top');" +
    "var tr=top.getBoundingClientRect();" +
    "var vr=vp.getBoundingClientRect();" +
    "var cs=getComputedStyle(vp);" +
    "return JSON.stringify({vh:window.innerHeight," +
    "cssHeight:cs.height, cssMaxH:cs.maxHeight," +
    "clientH:vp.clientHeight, clientW:vp.clientWidth," +
    "scrollH:vp.scrollHeight, scrollW:vp.scrollWidth," +
    "vpTop:Math.round(vr.top), vpBottom:Math.round(vr.bottom), vpLeft:Math.round(vr.left)," +
    "topH:Math.round(tr.height), topZ:getComputedStyle(top).zIndex," +
    "overlapTop:(vr.top < tr.bottom)});})()");
  console.log('VP:' + out);
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_vp.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9852
prof = os.path.join(OUT, "vpprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], URL],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=200)
child.kill()
for line in (r.stdout or "").splitlines():
    if line.startswith("VP:"):
        d = json.loads(line[3:])
        print("  视口窗口 %dx%d ｜ 顶栏高 %d" % (d["vh"], 0, d["topH"]))
        print("  .wy2-viewport  CSS height=%s  max-height=%s" % (d["cssHeight"], d["cssMaxH"]))
        print("  实际 client %dx%d ｜ 内容 %dx%d"
              % (d["clientW"], d["clientH"], d["scrollW"], d["scrollH"]))
        print("  位置 top=%d bottom=%d ｜ 顶栏底边=%d ｜ 与顶栏重叠=%s"
              % (d["vpTop"], d["vpBottom"], d["topH"], d["overlapTop"]))
        print("  纵向内容是否被纵向滚动条挤到: %s"
              % ("是（内容比窗口高）" if d["scrollH"] > d["clientH"] else "否"))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
try:
    os.remove(ns)
except OSError:
    pass
