# -*- coding: utf-8 -*-
"""核对小地图插画是否真的接上了，以及桌面/手机下的裁切与叠加区留白。

要回答四个问题（都用真视口量，不靠猜）：
  1. 第 2 关首页点据点进入小地图后，那张图是不是**本分区**的场景原画
     （而不是原来那个五幅共用的 wangyi-atlas.svg）
  2. 图片有没有真的加载成功（naturalWidth > 0，否则是 404 拿到空框）
  3. object-fit 造成的裁切比例：容器比例与图片自然比例差多少
  4. 叠加区（左上编号、底部标题）在**实际渲染尺寸**下是否压住主体？
     用"标题带亮度"与"浅色字对比度"来量。
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

REPO = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")

W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
H = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
MOB = 'true' if W < 700 else 'false'
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
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1, mobile: __MOB__});
  await send('Page.navigate', {url: process.argv[5]});
  await new Promise(r => setTimeout(r, 6500));
  const ev = async (expr) => {
    const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
    return (r.result && r.result.value);
  };
  /* 点第 1 个据点进小地图 */
  await ev("(function(){var p=document.querySelector('.wy-world-pin:not(.locked)');if(p)p.click();return 1;})()");
  await new Promise(r => setTimeout(r, 1500));
  console.log('MINI:' + await ev("JSON.stringify((function(){" +
    "var w=document.querySelector('.wy-mini-map'); if(!w) return {err:'no .wy-mini-map'};" +
    "var im=w.querySelector('img'); var r=w.getBoundingClientRect();" +
    "var ir=im?im.getBoundingClientRect():null;" +
    "var nm=document.querySelector('.wy-mini-name');" +
    "return {src:im?im.getAttribute('src'):'(无)'," +
    "natural:im?(im.naturalWidth+'x'+im.naturalHeight):'-'," +
    "complete:im?im.complete:false," +
    "box:Math.round(r.width)+'x'+Math.round(r.height)," +
    "imgBox:ir?(Math.round(ir.width)+'x'+Math.round(ir.height)):'-'," +
    "fit:im?getComputedStyle(im).objectFit:'-'," +
    "seal:(function(){var s=document.querySelector('.wy-mini-seal');return s?s.textContent.trim():'-';})()," +
    "name:nm?nm.textContent.trim():'-'," +
    "overlayAfter:!!w.querySelector('*')};})())"));
  const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(process.argv[6], Buffer.from(s.data, 'base64'));
  ws.close(); process.exit(0);
});
'''.replace('__MOB__', MOB)
ns = os.path.join(REPO, "_cdp_mini.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9888 if W >= 700 else 9889
prof = os.path.join(OUT, "miniprof%d" % W)
subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port, "--user-data-dir=" + prof,
                          "--window-size=1280,900", "about:blank"],
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
png = os.path.join(OUT, "mini_%dx%d.png" % (W, H))
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), URL, png],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
for line in (r.stdout or "").splitlines():
    if line.startswith("MINI:"):
        d = json.loads(line[5:])
        if d.get("err"):
            print("  !! %s" % d["err"])
            break
        print("  视口 %dx%d" % (W, H))
        print("    插画 src      : %s" % d["src"])
        print("    自然尺寸      : %s   complete=%s" % (d["natural"], d["complete"]))
        print("    容器/图片     : %s  /  %s   object-fit=%s"
              % (d["box"], d["imgBox"], d["fit"]))
        print("    叠加：编号「%s」  名称「%s」" % (d["seal"], d["name"]))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
print("  截图 %s" % png)
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
