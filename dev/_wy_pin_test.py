# -*- coding: utf-8 -*-
"""验证第二关大地图据点的三类行为。

三件必须量出来（不靠肉眼）：
  1. 五个据点都存在，且锁/解锁状态与 zoneOpenAt 的顺序解锁规则一致
     （初始进度下只有第 1 幅可进，其余 4 幅锁定）
  2. **锁定据点可点**——点击要给出"先完成哪幅地图"的说明
     （原来锁定时是无 onclick 的 div，点了毫无反馈）
  3. 点击已解锁据点会进入小地图

做法：用 CDP 真视口加载 #/play/wangyi-map，
读 DOM 拿据点状态，再派发真实 click 并抓 toast 文本。
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
    {width: 420, height: 900, deviceScaleFactor: 1, mobile: true});
  await send('Page.navigate', {url: process.argv[3]});
  await new Promise(r => setTimeout(r, 6000));

  const probe = "JSON.stringify((function(){" +
    "var pins=[].slice.call(document.querySelectorAll('.wy-world-pin'));" +
    "return {count:pins.length," +
    "list:pins.map(function(p,i){return {i:i+1," +
    "locked:p.classList.contains('locked')," +
    "lit:p.classList.contains('lit')," +
    "tag:p.tagName.toLowerCase()," +
    "aria:(p.getAttribute('aria-label')||'').slice(0,44)," +
    "w:Math.round(p.getBoundingClientRect().width)," +
    "h:Math.round(p.getBoundingClientRect().height)};})," +
    "zoneCards:document.querySelectorAll('.wy-zone-card').length," +
    "smallmapHeading:document.querySelectorAll('.wy-smallmap-heading').length};})())";
  const a = await send('Runtime.evaluate', {expression: probe, returnByValue: true});
  console.log('PINS:' + ((a.result && a.result.value) || '{}'));

  /* 点第一个锁定据点，抓 toast 文本 */
  const clickLocked = "JSON.stringify((function(){" +
    "var p=document.querySelector('.wy-world-pin.locked');" +
    "if(!p) return {err:'no locked pin'};" +
    "p.click();" +
    "return {clicked:true};})())";
  await send('Runtime.evaluate', {expression: clickLocked, returnByValue: true});
  await new Promise(r => setTimeout(r, 700));
  const t = await send('Runtime.evaluate', {expression:
    "JSON.stringify({toast:(function(){var e=document.querySelector('.toast');" +
    "return e?e.textContent.trim():'(无 toast)';})()})", returnByValue: true});
  console.log('TOAST:' + ((t.result && t.result.value) || '{}'));

  /* 点已解锁据点（第 1 个），应进入小地图 */
  const clickOpen = "JSON.stringify((function(){" +
    "var p=document.querySelector('.wy-world-pin:not(.locked)');" +
    "if(!p) return {err:'no open pin'}; p.click(); return {clicked:true};})())";
  await send('Runtime.evaluate', {expression: clickOpen, returnByValue: true});
  await new Promise(r => setTimeout(r, 900));
  const z = await send('Runtime.evaluate', {expression:
    "JSON.stringify({zoneTop:!!document.querySelector('.wy-zone-topline')," +
    "backBtn:(function(){var b=document.querySelector('.wy-back-map');" +
    "return b?b.textContent.trim():'(无返回按钮)';})()})", returnByValue: true});
  console.log('ZONE:' + ((z.result && z.result.value) || '{}'));

  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_wypin.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9822
prof = os.path.join(OUT, "wypinprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], URL],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)

for line in (r.stdout or "").splitlines():
    if line.startswith("PINS:"):
        d = json.loads(line[5:])
        print("  据点 %d 个；残留小地图卡片 %d 个；残留小地图标题 %d 个"
              % (d["count"], d["zoneCards"], d["smallmapHeading"]))
        for p in d["list"]:
            print("    %d  %-6s locked=%-5s lit=%-5s %dx%d  %s"
                  % (p["i"], p["tag"], p["locked"], p["lit"], p["w"], p["h"], p["aria"]))
    if line.startswith("TOAST:"):
        print("  点锁定据点的回应: " + json.loads(line[6:]).get("toast", "?"))
    if line.startswith("ZONE:"):
        d = json.loads(line[5:])
        print("  点已解锁据点 -> 进入小地图: %s ；返回按钮: %s" % (d["zoneTop"], d["backBtn"]))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
