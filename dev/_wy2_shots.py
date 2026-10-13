# -*- coding: utf-8 -*-
"""第二关交付截图（干净状态，不带自动化残留）。

只做"给人看"这一件事：大地图 → 小地图 → 局部放大 → 学习卡 → 手机宽度大地图。
所有页面滚动都归零，保证截图就是用户第一眼看到的样子。

用法：
  python dev/_wy2_shots.py 1440 1000 d
  python dev/_wy2_shots.py 390 844  m
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
URL = "http://127.0.0.1:8099/index.html#/play/wangyi-map"

W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
H = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
TAG = sys.argv[3] if len(sys.argv) > 3 else "d"

CDP = r'''
const ws = new WebSocket(process.argv[2]);
const W = +process.argv[3], H = +process.argv[4], TAG = process.argv[5];
const OUTDIR = process.argv[6];
const fs = require('fs');
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
const shot = async name => {
  const s = await send('Page.captureScreenshot', {format: 'png'});
  fs.writeFileSync(OUTDIR + '/' + name, Buffer.from(s.data, 'base64'));
};
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: W, height: H, deviceScaleFactor: 1, mobile: W < 700});
  await send('Page.navigate', {url: process.argv[7]});
  await sleep(6500);
  await ev("window.scrollTo(0,0)");
  await sleep(400);
  await shot('wy2-shot-' + TAG + '-1-world.png');

  /* 进「人居器物」（33 个字，物件最密的一区） */
  await ev("window.scrollTo(0,0)");
  await ev("(function(){var p=[].slice.call(document.querySelectorAll('.wy2-pin'))" +
    ".filter(function(e){return e.querySelector('b').textContent==='人居器物';})[0];" +
    "if(p) p.click();})()");
  await sleep(1500);
  await ev("window.scrollTo(0,0)");
  await sleep(400);
  await shot('wy2-shot-' + TAG + '-2-zone.png');

  /* 标出可点处：让"哪里有东西"一眼可见 */
  await ev("(function(){var b=[].slice.call(document.querySelectorAll('.wy2-tool'))" +
    ".filter(function(e){return e.textContent.indexOf('标出')>=0;})[0]; if(b) b.click();})()");
  await sleep(700);
  await ev("window.scrollTo(0,0)");
  await sleep(300);
  await shot('wy2-shot-' + TAG + '-3-hots.png');

  /* 点「鼎」：放大 → 学习卡。
     热点本身没有 aria-label，但同一分区里第 i 个 .wy2-spot 就对应
     数据里第 i 个 objects——从 _data.js 里查出「鼎」的序号再点。 */
  const t = await ev("(function(){" +
    "var zone=(App.levels.map.zones||[]).filter(function(z){return z.name==='人居器物';})[0];" +
    "if(!zone) return 'no-zone';" +
    "var idx=-1;" +
    "for(var i=0;i<zone.objects.length;i++){ if(zone.objects[i].char==='鼎'){idx=i;break;} }" +
    "if(idx<0) return 'no-char';" +
    "var vp=document.querySelector('.wy2-viewport');" +
    "var sp=document.querySelectorAll('.wy2-spot');" +
    "if(idx>=sp.length) return 'idx-oob';" +
    "var target=sp[idx];" +
    "var c=target.querySelector('.wy2-hit');" +
    "var vr=vp.getBoundingClientRect(), r=c.getBoundingClientRect();" +
    "vp.scrollLeft += Math.round((r.left+r.width/2)-(vr.left+vr.width/2));" +
    "vp.scrollTop  += Math.round((r.top+r.height/2)-(vr.top+vr.height/2));" +
    "r=c.getBoundingClientRect();" +
    "var x=Math.round((Math.max(r.left,vr.left)+Math.min(r.right,vr.right))/2);" +
    "var y=Math.round((Math.max(r.top,vr.top)+Math.min(r.bottom,vr.bottom))/2);" +
    "window.__tap={x:x,y:y}; return x+','+y;})()");
  let tp = {x: 0, y: 0};
  try { const q = t.split(','); tp = {x: +q[0], y: +q[1]}; } catch (e) {}
  await send('Input.dispatchMouseEvent',
    {type: 'mousePressed', x: tp.x, y: tp.y, button: 'left', clickCount: 1});
  await send('Input.dispatchMouseEvent',
    {type: 'mouseReleased', x: tp.x, y: tp.y, button: 'left', clickCount: 1});
  await sleep(900);
  await ev("window.scrollTo(0,0)");
  await sleep(300);
  await shot('wy2-shot-' + TAG + '-4-zoom.png');

  const t2 = await ev("(function(){" +
    "var vp=document.querySelector('.wy2-viewport');" +
    "var c=document.querySelector('.wy2-spot.focus .wy2-hit'); if(!c) return '';" +
    "var vr=vp.getBoundingClientRect(), r=c.getBoundingClientRect();" +
    "return Math.round((Math.max(r.left,vr.left)+Math.min(r.right,vr.right))/2)+','+" +
    "Math.round((Math.max(r.top,vr.top)+Math.min(r.bottom,vr.bottom))/2);})()");
  let tp2 = tp;
  try { const q = t2.split(','); if (q.length === 2) { tp2 = {x: +q[0], y: +q[1]}; } } catch (e) {}
  await send('Input.dispatchMouseEvent',
    {type: 'mousePressed', x: tp2.x, y: tp2.y, button: 'left', clickCount: 1});
  await send('Input.dispatchMouseEvent',
    {type: 'mouseReleased', x: tp2.x, y: tp2.y, button: 'left', clickCount: 1});
  await sleep(900);
  await shot('wy2-shot-' + TAG + '-5-card.png');
  console.log('DONE ' + t + ' | ' + t2);
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_wy2shot.js")
io.open(ns, "w", encoding="utf-8").write(
    CDP.replace("__OUTDIR__", OUT.replace("\\", "/")))

port = 9872
prof = os.path.join(OUT, "wy2shotprof")
if os.path.isdir(prof):
    subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port,
                          "--user-data-dir=" + prof, "--window-size=1500,1100",
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), TAG,
                    OUT.replace("\\", "/"), URL],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=300)
child.kill()
for line in (r.stdout or "").splitlines():
    if line.startswith("DONE"):
        print("  点击落点 " + line[5:])
if r.stderr:
    print("  stderr: " + r.stderr[:400])
shots = sorted(f for f in os.listdir(OUT) if f.startswith("wy2-shot-" + TAG))
print("  出图 %d 张：%s" % (len(shots), "\n            ".join(shots)))
try:
    os.remove(ns)
except OSError:
    pass
