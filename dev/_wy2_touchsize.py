# -*- coding: utf-8 -*-
"""量手机上**每个热点的可点直径**（CSS px），用来核对「触控范围适合手指」。

做法：真视口进某一区，把视口滚到热点中心，读该热点 hit 圆的
getBoundingClientRect（那是它在屏幕上的真实可点尺寸），
再按半径排序，把最小的十个列出来。

用法：python dev/_wy2_touchsize.py 390 844 人居器物
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

W = int(sys.argv[1]) if len(sys.argv) > 1 else 390
H = int(sys.argv[2]) if len(sys.argv) > 2 else 844
ZONE = sys.argv[3] if len(sys.argv) > 3 else "人居器物"

CDP = r'''
const ws = new WebSocket(process.argv[2]);
const W = +process.argv[3], H = +process.argv[4], ZONE = process.argv[5];
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
    {width: W, height: H, deviceScaleFactor: 1, mobile: W < 700});
  await send('Page.navigate', {url: process.argv[6]});
  await sleep(6500);
  await ev("(function(){var p=[].slice.call(document.querySelectorAll('.wy2-pin'))" +
    ".filter(function(e){return e.querySelector('b').textContent===" + JSON.stringify(ZONE) + ";})[0];" +
    "if(p) p.click();})()");
  await sleep(1600);
  const out = await ev("(function(){" +
    "var vp=document.querySelector('.wy2-viewport');" +
    "var st=document.querySelector('.wy2-stage');" +
    "var sr=st.getBoundingClientRect();" +
    "var scale=sr.width/2624;" +
    "var zone=(App.levels.map.zones||[]).filter(function(z){return z.name===" + JSON.stringify(ZONE) + ";})[0];" +
    "var sp=[].slice.call(document.querySelectorAll('.wy2-spot'));" +
    "var rows=[];" +
    "for(var i=0;i<sp.length&&i<zone.objects.length;i++){" +
    "var c=sp[i].querySelector('.wy2-hit'); var r=c.getBoundingClientRect();" +
    "rows.push({ch:zone.objects[i].char,r:zone.objects[i].r," +
    "d:Math.round(r.width),px:Math.round(r.width*1)});}" +
    "rows.sort(function(a,b){return a.d-b.d;});" +
    "return JSON.stringify({scale:scale,vpw:vp.clientWidth,vph:vp.clientHeight," +
    "stageW:Math.round(sr.width),n:rows.length,small:rows.slice(0,12)});})()");
  console.log('TOUCH:' + out);
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_touch.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9882
prof = os.path.join(OUT, "touchprof")
if os.path.isdir(prof):
    subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port,
                          "--user-data-dir=" + prof, "--window-size=1000,900",
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), ZONE, URL],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=200)
child.kill()
for line in (r.stdout or "").splitlines():
    if line.startswith("TOUCH:") and len(line) > 6:
        d = json.loads(line[6:])
        print("=" * 70)
        print("  手机触控尺寸 · %dx%d · 分区「%s」" % (W, H, ZONE))
        print("=" * 70)
        print("  缩放比例 %.4f（图 %d 用户单位 → 屏幕 %d px）"
              % (d["scale"], 2624, d["stageW"]))
        print("  视口 %dx%d ｜ 热点 %d 个" % (d["vpw"], d["vph"], d["n"]))
        print("  最小的 12 个可点直径（CSS px）：")
        for x in d["small"]:
            flag = "  ← 小于 44" if x["d"] < 44 else ""
            print("    %-3s r=%-4d  直径 %3dpx%s" % (x["ch"], x["r"], x["d"], flag))
        bad = [x for x in d["small"] if x["d"] < 44]
        print("  小结：最小 %dpx，%d 个小于 44px（44px 是手指可靠可点的下限）"
              % (d["small"][0]["d"] if d["small"] else 0, len(bad)))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
try:
    os.remove(ns)
except OSError:
    pass
