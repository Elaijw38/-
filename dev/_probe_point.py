# -*- coding: utf-8 -*-
"""点探：在真实视口里取某一点，报出该点上所有元素的盒模型与边框。

起因：整页截图里出现一条横贯全宽的细线，肉眼能看到但不知道该怪谁。
靠"猜是哪个元素的 border" 不如直接问 DOM。用 document.elementsFromPoint
拿到该点自下而上的命中栈，再把 borderTop/Bottom、背景与尺寸打出来。

用法：python dev/_probe_point.py <route> <宽> <高> <x> <y> [滚动到]
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
PX = int(sys.argv[4]) if len(sys.argv) > 4 else 100
PY = int(sys.argv[5]) if len(sys.argv) > 5 else 632
Y = int(sys.argv[6]) if len(sys.argv) > 6 else 1100

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
  /* 注意：**不要**在这里开 Log.enable / Runtime.enable——
     实测开了之后场景就不再挂载（#sceneRoot 空、页面恒 394px）。
     _route_shot.py 只用 Page.enable，一直是好的。 */
  await send('Emulation.setDeviceMetricsOverride',
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: process.argv[5]});
  /* 固定等一拍就好。**不要**在这里反复 evaluate 去"等页面高度稳定"——
     试过，反复轮询会让页面停在 394px 不再长高（同一个 URL，_scroll_diag
     只是老老实实等 5s，就拿得到 3181px 的真实高度）。
     也不要 dispatch resize 去"催"布局，同样会把挂载搞坏。 */
  await new Promise(r => setTimeout(r, 6000));
  /* 滚两遍：第一遍之后布局可能还会长高，第二遍才到位 */
  if (+process.argv[8] > 0) {
    await send('Runtime.evaluate', {expression: 'window.scrollTo(0,' + process.argv[8] + ')'});
    await new Promise(r => setTimeout(r, 700));
    await send('Runtime.evaluate', {expression: 'window.scrollTo(0,' + process.argv[8] + ')'});
    await new Promise(r => setTimeout(r, 700));
    await send('Runtime.evaluate', {expression: 'window.scrollTo(0,' + process.argv[8] + ')'});
    await new Promise(r => setTimeout(r, 1200));
  }
  /* 先单独量一次，确认页面真的长起来了；量不到就直接报出来，
     免得后面所有元素查询都返回空、看起来像"样式没生效"。 */
  const m = await send('Runtime.evaluate', {expression:
    'document.documentElement.scrollHeight + "|" + window.innerHeight + "|" +' +
    '(document.querySelector("#sceneRoot") ? document.querySelector("#sceneRoot").children.length : -1) + "|" +' +
    'document.querySelectorAll(".atlas-card").length', returnByValue: true});
  console.log('MEASURE:' + ((m.result && m.result.value) || 'n/a'));
  const st = await send('Runtime.evaluate', {expression:
    'JSON.stringify({y:Math.round(window.scrollY),' +
    'docH:document.documentElement.scrollHeight,innerH:window.innerHeight,hash:location.hash,' +
    'hitY:(function(){var e=document.elementsFromPoint(PXVAL,PYVAL);' +
    'return e.length?(""+(e[0].className||e[0].tagName)):"";})(),' +
    /* 顺手量第一张拓片上的字形：SVG 的 stroke-width 是**表现属性**，
       CSS 能盖住它——但要确认真的盖住了，且透明度别把反白字压到读不出 */
    'glyph:(function(){var g=document.querySelector(".ac-glyph");if(!g)return null;' +
    'var cs=getComputedStyle(g),r=g.getBoundingClientRect();' +
    'var p=g.querySelector("path");' +
    'return {w:Math.round(r.width),h:Math.round(r.height),' +
    'cssSW:cs.strokeWidth,color:cs.color,op:cs.opacity,' +
    'pathSW:p?getComputedStyle(p).strokeWidth:"-",' +
    'attrSW:(p&&p.getAttribute("stroke-width"))||"-",' +
    'obOp:getComputedStyle(g.parentNode).opacity};})()})',
    returnByValue: true});
  console.log('STATE:' + ((st.result && st.result.value) || ''));
  /* 注意：这段表达式是在**页面**里跑的，页面里没有 process/argv，
     所以坐标必须由 Python 直接插值进来，不能读 process.argv。 */
  const expr = "JSON.stringify((function(){var px=__PX__, py=__PY__;" +
    "var els=document.elementsFromPoint(px,py); return els.slice(0,8).map(function(e){" +
    "var cs=getComputedStyle(e), r=e.getBoundingClientRect();" +
    "return {tag:e.tagName.toLowerCase(), cls:(e.className||'').toString().slice(0,70)," +
    " w:Math.round(r.width), h:Math.round(r.height), top:Math.round(r.top), bot:Math.round(r.bottom)," +
    " bt:cs.borderTopWidth+' '+cs.borderTopColor, bb:cs.borderBottomWidth+' '+cs.borderBottomColor," +
    " bgi:(cs.backgroundImage||'').slice(0,40), bgc:cs.backgroundColor, op:cs.opacity};});})())";
  const a = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  console.log('HITS:' + ((a.result && a.result.value) || ''));
  ws.close(); process.exit(0);
});
'''.replace('__PX__', str(PX)).replace('__PY__', str(PY)) \
   .replace('PXVAL', str(PX)).replace('PYVAL', str(PY))
ns = os.path.join(REPO, "_cdp_probe.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9766
prof = os.path.join(OUT, "probeprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), URL, str(PX), str(PY), str(Y)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
for line in (r.stdout or "").splitlines():
    if line.startswith("MEASURE:"):
        p = line[8:].split("|")
        print("  量: scrollHeight=%s innerHeight=%s #sceneRoot子元素=%s .atlas-card=%s"
              % tuple(p) if len(p) == 4 else ("  量: " + line[8:]))
    if line.startswith("STATE:"):
        print("  状态 " + line[6:])
    if line.startswith("HITS:"):
        hits = json.loads(line[5:])
        print("  点 (%d,%d) 处的命中栈（上→下）：" % (PX, PY))
        for h in hits:
            print("    %-6s .%-14s %4dx%-5d top=%-5d bot=%-5d  BT=%s  BB=%s  bg=%s"
                  % (h["tag"], h["cls"][:14], h["w"], h["h"], h["top"], h["bot"],
                     h["bt"], h["bb"], h["bgc"]))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
