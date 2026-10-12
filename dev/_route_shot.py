# -*- coding: utf-8 -*-
"""按路由截图（CDP 真视口）。

与 _scroll_shot.py 的区别：那个是看首页各分区的节奏，这个只想快速看
**某一个路由**长什么样（图鉴 / 说明 / 设置……）。用真实 CDP 视口设置，
不用 Edge 的 --window-size——它有个 482px 的最小宽度下限，
量手机端会得到"假结论"（见 HANDOFF 的坑表）。

用法：python dev/_route_shot.py <route> <宽> <高> <输出png> [滚动到]
      route 例：atlas / modes / howto / settings / home / play/bone-build
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
PNG = sys.argv[4] if len(sys.argv) > 4 else os.path.join(OUT, "route.png")
Y = int(sys.argv[5]) if len(sys.argv) > 5 else 0

URL = "http://127.0.0.1:8099/index.html#/" + ROUTE.lstrip("#/").lstrip("/")

# 顺便把几个关键量算出来：横向溢出、ground 的实际计算值、
# 以及骨材质那一层到底有没有生效（backgroundImage 里能不能找到 bone.png）。
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
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1, mobile: +process.argv[3] < 700});
  await send('Page.navigate', {url: process.argv[5]});
  await new Promise(r => setTimeout(r, 4500));
  if (process.argv[7] && +process.argv[7] > 0) {
    await send('Runtime.evaluate', {expression: 'window.scrollTo(0,' + process.argv[7] + ')'});
    await new Promise(r => setTimeout(r, 1500));
  }
  const expr = "JSON.stringify((function(){var b=getComputedStyle(document.body);" +
    "var de=document.documentElement;return {" +
    "bgImage:(b.backgroundImage||'').indexOf('bone.png')>=0," +
    "bgBlend:b.backgroundBlendMode," +
    "bgSize:b.backgroundSize," +
    "bgColor:b.backgroundColor," +
    "docW:de.scrollWidth, winW:window.innerWidth," +
    "overflowX:de.scrollWidth-window.innerWidth," +
    "obLen:((getComputedStyle(de).getPropertyValue('--ob-pattern'))||'').length," +
    "sheets:document.querySelectorAll('.sheet').length," +
    "atlasCards:document.querySelectorAll('.atlas-card').length," +
    "sceneKids:document.querySelector('#sceneRoot')?document.querySelector('#sceneRoot').children.length:-1," +
    /* 拓片上的字形：SVG 的 stroke-width 是**表现属性**，CSS 应当盖得住它。
       这里把 CSS 计算值与属性值都取回来，确认真的盖住了，别靠猜。 */
    "glyph:(function(){var g=document.querySelector('.ac-glyph');if(!g)return null;" +
      "var cs=getComputedStyle(g),p=g.querySelector('path');" +
      "return {w:Math.round(g.getBoundingClientRect().width)," +
      "cssSW:cs.strokeWidth,color:cs.color,op:cs.opacity," +
      "pathSW:p?getComputedStyle(p).strokeWidth:'-'," +
      "pathColor:p?getComputedStyle(p).stroke:'-'," +
      "attrSW:p?(p.getAttribute('stroke-width')||'-'):'-'};})()," +
    "route:(location.hash||'')};})())";
  const a = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  console.log('INFO:' + ((a.result && a.result.value) || ''));
  const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(process.argv[6], Buffer.from(s.data, 'base64'));
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_route.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9722
prof = os.path.join(OUT, "routeprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), URL, PNG, str(Y)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
for line in (r.stdout or "").splitlines():
    if line.startswith("INFO:"):
        info = json.loads(line[5:])
        print("  路由 %s   视口 %dx%d" % (info["route"], W, H))
        print("  骨材质层生效=%s   blend=%s" % (info["bgImage"], info["bgBlend"]))
        print("  底色 %s   size=%s" % (info["bgColor"], info["bgSize"]))
        print("  横向溢出 %dpx（doc %d / win %d）"
              % (info["overflowX"], info["docW"], info["winW"]))
        print("  刻辞底纹 %d 字符   .sheet=%d   .atlas-card=%d   #sceneRoot子元素=%d"
              % (info["obLen"], info["sheets"], info["atlasCards"], info["sceneKids"]))
        g = info.get("glyph")
        if g:
            print("  拓片字形：宽 %dpx  CSS stroke-width=%s（属性 %s，计算后 %s）"
                  % (g["w"], g["cssSW"], g["attrSW"], g["pathSW"]))
            print("            color=%s  stroke=%s  opacity=%s"
                  % (g["color"], g["pathColor"], g["op"]))
        else:
            print("  拓片字形：未取到（该路由没有 .ac-glyph）")
if r.stderr:
    print("  stderr: " + r.stderr[:300])
print("  截图 %s  %d B" % (PNG, os.path.getsize(PNG) if os.path.exists(PNG) else 0))
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
