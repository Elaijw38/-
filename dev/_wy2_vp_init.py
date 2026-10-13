# -*- coding: utf-8 -*-
"""量"进入小地图后的初始视口"：位置、尺寸、滚动量。

用途：确认手机上刚进小地图时图上沿（含最上排热点）到底在屏幕哪里，
而不是靠一张截图猜。可指定宽度/高度与分区名。
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
  .then(r => { if (r && r.exceptionDetails) {
      return 'JSEXC:' + ((r.exceptionDetails.exception && r.exceptionDetails.exception.description) ||
                         r.exceptionDetails.text || '?');
    } return (r.result && r.result.value) || ''; });
const probe = () => ev("(function(){" +
  "var vp=document.querySelector('.wy2-viewport');" +
  "if(!vp) return JSON.stringify({noVp:true," +
    "view:(document.querySelector('.wy2-pin')?'world':'其他')," +
    "winScrollY:Math.round(window.scrollY)});" +
  "var st=document.querySelector('.wy2-stage');" +
  "var art=document.querySelector('.wy2-art');" +
  "var rect=function(e){if(!e)return null;var r=e.getBoundingClientRect();" +
    "return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)];};" +
  "return JSON.stringify({winScrollY:Math.round(window.scrollY)," +
  "vp:rect(vp), stage:rect(st), art:rect(art)," +
  "client:[vp.clientWidth,vp.clientHeight]," +
  "scroll:[Math.round(vp.scrollLeft),Math.round(vp.scrollTop)]," +
  "content:[Math.round(vp.scrollWidth),Math.round(vp.scrollHeight)]," +
  "activeTag:(document.activeElement&&document.activeElement.tagName)||'-'," +
  "activeCls:(document.activeElement&&document.activeElement.className)||'-'});})()");
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: W, height: H, deviceScaleFactor: 1, mobile: W < 700});
  await send('Page.navigate', {url: process.argv[6]});
  await sleep(6000);
  console.log('WORLD ' + await probe());
  await ev("(function(){var p=[].slice.call(document.querySelectorAll('.wy2-pin'))" +
    ".filter(function(e){return e.querySelector('b').textContent===" + JSON.stringify(ZONE) + ";})[0];" +
    "if(p) p.click(); return p?'clicked':'no-pin';})()");
  await sleep(500);
  console.log('JUST-ENTERED ' + await probe());
  await sleep(2000);
  console.log('AFTER-2s ' + await probe());
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_vp2.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9862
prof = os.path.join(OUT, "vp2prof")
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
sys.stderr.write("RAW OUT:\n" + (r.stdout or "(空)") + "\nRAW ERR:\n" + (r.stderr or "(空)") + "\n")
print("=" * 66)
print("  小地图初始视口 · %dx%d · 分区「%s」" % (W, H, ZONE))
print("=" * 66)
for line in (r.stdout or "").splitlines():
    for tag in ("WORLD ", "JUST-ENTERED ", "AFTER-2s "):
        if line.startswith(tag) and len(line) > len(tag):
            d = json.loads(line[len(tag):])
            if d.get("noVp"):
                print("%-14s 还没进小地图（%s）页面滚动 y=%s"
                      % (tag.strip(), d.get("view"), d.get("winScrollY")))
                continue
            print("%-14s 页面滚动 y=%-5s 视口 %s 客户端 %s"
                  % (tag.strip(), d["winScrollY"], d["vp"], d["client"]))
            print("%-14s 舞台 %s 内容 %s 滚动 %s"
                  % ("", d["stage"], d["content"], d["scroll"]))
            print("%-14s 聚焦=%s.%s" % ("", d["activeTag"], d["activeCls"]))
if r.stderr:
    print("  stderr: " + r.stderr[:600])
if not (r.stdout or "").strip():
    print("  !! node 没有输出；stderr 见上")
try:
    os.remove(ns)
except OSError:
    pass
