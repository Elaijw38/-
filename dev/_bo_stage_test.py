# -*- coding: utf-8 -*-
"""核对第三关（构件讨伐 / Boss 战）是否仍突出"拆解字形"，以及龟宝的反应对不对。

任务书要求：
  · 保留 Boss 分阶段挑战与现有战斗界面
  · 龟宝作为玩家代表，对**答对 / 答错 / 破防 / 阶段变化**给出对应反应与提示
  · 仍突出甲骨字形学习与拆解过程，不要退化成普通题目列表

逐条量：
  1. 三阶段指示器存在且第 1 阶段高亮
  2. 龟宝化身在场（.bd-player-name = 龟宝）且带 mood-* 情绪类
  3. 龟宝提示随状态变化：先读初始文案，再故意点错一块，读变化后的文案
  4. 拆解机制的证据：存在构件池/笔画池（.bd-chip）与形体完整度进度条
"""
import io
import json
import os
import subprocess
import time
import urllib.request

REPO = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")
URL = "http://127.0.0.1:8099/index.html#/play/boss-raid"

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
    {width: 1280, height: 900, deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: process.argv[3]});
  await new Promise(r => setTimeout(r, 6000));
  const ev = async (expr) => {
    const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
    return (r.result && r.result.value);
  };

  /* 选关 -> 进第 1 关 */
  const enter = await ev("(function(){var b=document.querySelector('.bo-bead');if(b){b.click();return 'bead';}" +
    "var a=document.querySelector('[data-level],.bo-card,.bo-enter');if(a){a.click();return 'other';}return 'none';})()");
  console.log('ENTER:' + JSON.stringify({how: enter}));
  await new Promise(r => setTimeout(r, 1200));

  console.log('FIGHT:' + await ev("JSON.stringify({" +
    "player:(function(){var e=document.querySelector('.bd-player-name');return e?e.textContent.trim():'(无)';})()," +
    "mood:(function(){var e=document.querySelector('.bd-hero-portrait');if(!e)return '(无)';" +
      "return [].slice.call(e.classList).filter(function(c){return c.indexOf('mood-')===0;}).join(',')||'(无 mood 类)';})()," +
    "phases:document.querySelectorAll('.bd-phase').length," +
    "phaseOn:(function(){var e=document.querySelector('.bd-phase.on');return e?e.textContent.trim():'(无)';})()," +
    "guideKicker:(function(){var e=document.querySelector('.bd-guide-kicker');return e?e.textContent.trim():'(无)';})()," +
    "guideTitle:(function(){var e=document.querySelector('.bd-guide-title');return e?e.textContent.trim():'(无)';})()," +
    "guideText:(function(){var e=document.querySelector('.bd-guide-copy');return e?e.textContent.trim():'(无)';})()," +
    "chips:document.querySelectorAll('.bd-chip').length," +
    "hasBossGlyph:!!document.querySelector('.bd-body,.bd-bodybox')," +
    "hasIntegrity:!!document.querySelector('.bd-sidebar')})"));

  /* 故意点错一块构件 -> 看龟宝是否换成"再观察一次"这类反应 */
  const miss = await ev("(function(){var c=document.querySelector('.bd-chip:not([disabled])');" +
    "if(c){c.click();return 'clicked';}return 'none';})()");
  await new Promise(r => setTimeout(r, 900));
  console.log('AFTERMISS:' + await ev("JSON.stringify({" +
    "clicked:" + JSON.stringify(miss) + "," +
    "mood:(function(){var e=document.querySelector('.bd-hero-portrait');if(!e)return '(无)';" +
      "return [].slice.call(e.classList).filter(function(c){return c.indexOf('mood-')===0;}).join(',')||'(无 mood 类)';})()," +
    "guideTitle:(function(){var e=document.querySelector('.bd-guide-title');return e?e.textContent.trim():'(无)';})()," +
    "guideText:(function(){var e=document.querySelector('.bd-guide-copy');return e?e.textContent.trim():'(无)';})()," +
    "logCount:document.querySelectorAll('.bd-log').length})"));

  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_bo.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9866
prof = os.path.join(OUT, "boprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], URL],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)

for line in (r.stdout or "").splitlines():
    tag, _, payload = line.partition(":")
    try:
        d = json.loads(payload)
    except Exception:
        continue
    if tag == "ENTER":
        print("  进入战斗方式: %s" % d.get("how"))
    elif tag == "FIGHT":
        print("  龟宝化身: %s   情绪类: %s" % (d.get("player"), d.get("mood")))
        print("  阶段指示: %d 个，当前高亮「%s」" % (d.get("phases"), d.get("phaseOn")))
        print("  龟宝提示: [%s] %s" % (d.get("guideKicker"), d.get("guideTitle")))
        print("      %s" % d.get("guideText"))
        print("  构件池: %d 个可点构件   甲骨字形在场=%s   形体完整度条=%s"
              % (d.get("chips"), d.get("hasBossGlyph"), d.get("hasIntegrity")))
    elif tag == "AFTERMISS":
        print("  点错一块后（%s）：" % d.get("clicked"))
        print("      情绪类 -> %s" % d.get("mood"))
        print("      提示 -> %s ｜ %s" % (d.get("guideTitle"), d.get("guideText")))
        print("      战斗日志 %d 条" % d.get("logCount"))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
