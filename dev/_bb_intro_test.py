# -*- coding: utf-8 -*-
"""核对第一关（甲骨构字 / 入门课）是否满足"低压力入门"的四条要求。

要求（来自任务书）：
  · 定位初步入门，不是高压战斗关
  · 在轻量操作中观察字形、拼合构件，过程中获得甲骨知识讲解
  · 龟宝在关键操作后给简短提示、解释字形与鼓励，且与当前字/操作相关
  · 宽容、可重复尝试，**无倒计时、无惩罚式失败**

这里逐条量：
  1. 页面上有没有倒计时/计时器元素（.timer / 倒计时 文案）——应无
  2. 有没有"生命/血量/失败"这类惩罚性元素——应无
  3. 入门课是否 5 题、是否有"请龟宝给线索"按钮
  4. 提交错误后是否仍可继续（不锁死、有提示文案）
  5. 龟宝讲解是否出现、且带当前字的信息
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
URL = "http://127.0.0.1:8099/index.html#/play/bone-build"

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

  /* 封面 */
  console.log('COVER:' + await ev("JSON.stringify({title:(function(){var e=document.querySelector('.bb-cover-title');return e?e.textContent.replace(/\\s+/g,' ').trim():'(无)';})()," +
    "promises:[].slice.call(document.querySelectorAll('.bb-course-promise span,.bb-course-promise li')).map(function(e){return e.textContent.trim();})," +
    "startBtn:!!document.querySelector('.bb-start')," +
    "timer:document.querySelectorAll('.timer,.bb-timer,[class*=countdown]').length," +
    "lives:document.querySelectorAll('[class*=life],[class*=hp-],[class*=heart]').length})"));

  /* 进课 */
  await ev("(function(){var b=document.querySelector('.bb-start');if(b)b.click();return 1;})()");
  await new Promise(r => setTimeout(r, 900));
  console.log('LESSON:' + await ev("JSON.stringify({" +
    "progress:(function(){var e=document.querySelector('.bb-lesson-progress');return e?e.textContent.trim():'(无)';})()," +
    "hintBtn:(function(){var e=document.querySelector('.bb-hint-btn');return e?e.textContent.trim():'(无)';})()," +
    "submitBtn:(function(){var e=document.querySelector('.bb-intro-actions .btn.primary');return e?e.textContent.trim():'(无)';})()," +
    "fact:(function(){var e=document.querySelector('.bb-live-fact');return e?e.textContent.replace(/\\s+/g,' ').trim().slice(0,90):'(无)';})()," +
    "choices:document.querySelectorAll('.bb-intro-choice').length," +
    "timer:document.querySelectorAll('.timer,.bb-timer,[class*=countdown]').length})"));

  /* 故意提交错误（不选任何构件） */
  await ev("(function(){var b=document.querySelector('.bb-intro-actions .btn.primary');if(b)b.click();return 1;})()");
  await new Promise(r => setTimeout(r, 700));
  console.log('WRONG:' + await ev("JSON.stringify({" +
    "verdict:(function(){var e=document.querySelector('.bb-intro-verdict');return e?e.textContent.trim():'(无)';})()," +
    "stillHasSubmit:!!document.querySelector('.bb-intro-actions .btn.primary')," +
    "stillHasChoices:document.querySelectorAll('.bb-intro-choice').length})"));

  /* 点龟宝线索 */
  await ev("(function(){var b=document.querySelector('.bb-hint-btn');if(b)b.click();return 1;})()");
  await new Promise(r => setTimeout(r, 700));
  console.log('HINT:' + await ev("JSON.stringify({" +
    "verdict:(function(){var e=document.querySelector('.bb-intro-verdict');return e?e.textContent.trim():'(无)';})()," +
    "selected:document.querySelectorAll('.bb-intro-choice.selected').length})"));

  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_bb.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9844
prof = os.path.join(OUT, "bbprof")
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
    if ":" not in line:
        continue
    tag, _, payload = line.partition(":")
    try:
        d = json.loads(payload)
    except Exception:
        continue
    if tag == "COVER":
        print("  封面：%s" % d.get("title"))
        print("    承诺：%s" % " / ".join(d.get("promises") or []))
        print("    开始按钮=%s  计时器元素=%d  惩罚类元素=%d"
              % (d.get("startBtn"), d.get("timer"), d.get("lives")))
    elif tag == "LESSON":
        print("  入门课：%s   可选构件 %d 个   计时器元素=%d"
              % (d.get("progress"), d.get("choices"), d.get("timer")))
        print("    按钮：%s ｜ %s" % (d.get("hintBtn"), d.get("submitBtn")))
        print("    龟宝小课堂：%s" % d.get("fact"))
    elif tag == "WRONG":
        print("  提交错误后：判定文案「%s」" % d.get("verdict"))
        print("    仍可提交=%s  仍可选构件=%d（可重复尝试）"
              % (d.get("stillHasSubmit"), d.get("stillHasChoices")))
    elif tag == "HINT":
        print("  点龟宝线索后：「%s」  已选构件 %d 个"
              % (d.get("verdict"), d.get("selected")))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
