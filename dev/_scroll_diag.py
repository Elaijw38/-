# -*- coding: utf-8 -*-
"""页面滚动诊断：到底谁在滚、能不能滚。

起因：用 window.scrollTo 滚不动（scrollY 恒为 0），但整页截图明明是长的。
与其猜，不如把 html/body/.wrap/.app-shell 的 overflow、scrollHeight、clientHeight
全列出来，看谁才是真正的滚动容器。

用法：python dev/_scroll_diag.py <route> <宽> <高>
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

ROUTE = sys.argv[1] if len(sys.argv) > 1 else "home"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1440
H = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
URL = "http://127.0.0.1:8099/index.html#/" + ROUTE.lstrip("#/").lstrip("/")

CDP = r'''
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: process.argv[5]});
  await new Promise(r => setTimeout(r, 5000));
  const expr = "JSON.stringify((function(){" +
    "function d(sel){var e=sel==='html'?document.documentElement:" +
      "(sel==='body'?document.body:document.querySelector(sel));" +
      "if(!e)return {sel:sel,miss:true}; var cs=getComputedStyle(e);" +
      "return {sel:sel, oy:cs.overflowY, ox:cs.overflowX, pos:cs.position," +
      " sh:e.scrollHeight, ch:e.clientHeight, off:e.offsetHeight};}" +
    "var out=[d('html'),d('body'),d('.wrap'),d('.app-shell'),d('#sceneRoot'),d('.scene')];" +
    "var scr=[];document.querySelectorAll('*').forEach(function(e){" +
      "if(e.scrollHeight-e.clientHeight>40){var cs=getComputedStyle(e);" +
      "if(cs.overflowY==='auto'||cs.overflowY==='scroll'){" +
      "scr.push({cls:(e.className||e.tagName).toString().slice(0,50),sh:e.scrollHeight,ch:e.clientHeight});}}});" +
    "return {boxes:out, scrollers:scr.slice(0,8)," +
    "winY:Math.round(window.scrollY), docSH:document.documentElement.scrollHeight," +
    "bodySH:document.body.scrollHeight, innerH:window.innerHeight};})())";
  const a = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  console.log('DIAG:' + ((a.result && a.result.value) || ''));
  /* 试一下滚到底，看能不能动 */
  await send('Runtime.evaluate', {expression: 'window.scrollTo(0, 99999)'});
  await new Promise(r => setTimeout(r, 900));
  const b = await send('Runtime.evaluate', {expression:
    'JSON.stringify({afterY:Math.round(window.scrollY)})', returnByValue: true});
  console.log('AFTER:' + ((b.result && b.result.value) || ''));
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_diag.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9788
prof = os.path.join(OUT, "diagprof")
subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port, "--user-data-dir=" + prof,
                          "--window-size=1200,900", "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
targets = None
for _ in range(60):
    time.sleep(0.4)
    try:
        targets = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=10))
        if any(t.get("type") == "page" and t.get("webSocketDebuggerUrl") for t in targets):
            break
    except Exception:
        pass
page = [t for t in (targets or []) if t.get("type") == "page" and t.get("webSocketDebuggerUrl")][0]
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), URL],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
for line in (r.stdout or "").splitlines():
    if line.startswith("DIAG:"):
        d = json.loads(line[5:])
        print("  viewport innerHeight=%d  docScrollHeight=%d  bodyScrollHeight=%d  winY=%d"
              % (d["innerH"], d["docSH"], d["bodySH"], d["winY"]))
        print("  —— 各层盒模型 ——")
        for b in d["boxes"]:
            if b.get("miss"):
                print("    %-12s 不存在" % b["sel"])
            else:
                print("    %-12s overflowY=%-8s pos=%-8s scrollH=%-6d clientH=%-6d offsetH=%d"
                      % (b["sel"], b["oy"], b["pos"], b["sh"], b["ch"], b["off"]))
        print("  —— 内部可滚动容器 ——")
        if not d["scrollers"]:
            print("    （无）")
        for s in d["scrollers"]:
            print("    .%-30s scrollH=%-6d clientH=%d" % (s["cls"], s["sh"], s["ch"]))
    if line.startswith("AFTER:"):
        print("  滚到底之后 winY=" + str(json.loads(line[6:])["afterY"]))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
