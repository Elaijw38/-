# -*- coding: utf-8 -*-
"""关卡展板 · 交互测试（CDP 真事件）。

要验的四件事，都要用真实事件、不能只看代码：
  1 悬停某一块：它放大、其余弱化
  2 悬停时细节层（构件拆解 / 印章 / 古今对照 / 蓝图点位）显现
  3 放大后**不被裁**（父级没有 overflow:hidden 截断）
  4 点击真的能进对应关卡（路由变化 + 进到对局页）

用法：python dev/_lv_test.py [宽] [高]
"""
import io, json, os, subprocess, sys, time, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
H = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
PNG = os.path.join(OUT, "ui", "lv_hover_%dx%d.png" % (W, H))

PROBE = r"""(function(){
  function box(s){var e=document.querySelector(s);if(!e)return null;var r=e.getBoundingClientRect();
    return {t:Math.round(r.top+window.scrollY),l:Math.round(r.left),w:Math.round(r.width),h:Math.round(r.height)};}
  var panels = [].slice.call(document.querySelectorAll('.lv'));
  var st = getComputedStyle(document.querySelector('.lv:hover') || panels[0]);
  // 被 hover 的那块的标识
  var hov = null;
  for (var i=0;i<panels.length;i++){ if (panels[i].matches(':hover')) { hov = i; } }
  var out = {
    n: panels.length,
    hovered: hov,
    row: box('.lv-row'),
    panels: panels.map(function(p){
      var cs = getComputedStyle(p);
      return { w: Math.round(p.getBoundingClientRect().width),
               h: Math.round(p.getBoundingClientRect().height),
               op: cs.opacity, tr: cs.transform,
               center: p.className.indexOf('lv-center') >= 0,
               name: (p.querySelector('.lv-name')||{}).textContent,
               href: p.getAttribute('href'),
               breakOp: p.querySelector('.lv-break') ? getComputedStyle(p.querySelector('.lv-break')).opacity : null,
               sealOp: p.querySelector('.lv-seal') ? getComputedStyle(p.querySelector('.lv-seal')).opacity : null,
               modernOp: p.querySelector('.lv-modern') ? getComputedStyle(p.querySelector('.lv-modern')).opacity : null,
               dots: p.querySelectorAll('.lv-dot').length };
    }),
    docW: document.documentElement.clientWidth,
    sw: document.documentElement.scrollWidth
  };
  return JSON.stringify(out);
})()"""

CDP = r'''
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
const ev = async (type, x, y, extra) => send('Input.dispatchMouseEvent',
  Object.assign({type, x, y, button: 'left', clickCount: 1}, extra || {}));

ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1, mobile: +process.argv[9] === 1});
  await send('Page.navigate', {url: process.argv[5]});
  await new Promise(r => setTimeout(r, 4200));

  const before = await send('Runtime.evaluate', {expression: process.argv[6], returnByValue: true});
  console.log('BEFORE:' + ((before.result && before.result.value) || ''));

  // 悬停第 2 块（中心板）
  const b = await send('Runtime.evaluate', {expression:
    "(function(){var p=document.querySelectorAll('.lv')[1];var r=p.getBoundingClientRect();" +
    "return JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)});})()",
    returnByValue: true});
  const pt = JSON.parse(b.result.value);
  await ev('mouseMoved', pt.x, pt.y);
  await new Promise(r => setTimeout(r, 900));
  const after = await send('Runtime.evaluate', {expression: process.argv[6], returnByValue: true});
  console.log('AFTER:' + ((after.result && after.result.value) || ''));

  const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(process.argv[7], Buffer.from(s.data, 'base64'));

  // 离开后点击第 3 块，看是否进关
  await ev('mouseMoved', 5, 5);
  await new Promise(r => setTimeout(r, 300));
  const b3 = await send('Runtime.evaluate', {expression:
    "(function(){var p=document.querySelectorAll('.lv')[2];var r=p.getBoundingClientRect();" +
    "return JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),href:p.getAttribute('href')});})()",
    returnByValue: true});
  const p3 = JSON.parse(b3.result.value);
  await ev('mouseMoved', p3.x, p3.y);
  await ev('mousePressed', p3.x, p3.y);
  await ev('mouseReleased', p3.x, p3.y);
  await new Promise(r => setTimeout(r, 2600));
  const nav = await send('Runtime.evaluate', {expression:
    "JSON.stringify({hash: location.hash, scene: (document.querySelector('#sceneRoot .scene')||{}).className || ''," +
    " err: /加载出错|Uncaught/.test(document.documentElement.innerHTML)})",
    returnByValue: true});
  console.log('NAV:' + nav.result.value);

  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_lv.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9588
prof = os.path.join(OUT, "lvprof_t")
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

url = "file:///" + os.path.join(REPO, "index.html").replace("\\", "/") + "#/modes"
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), url, PROBE, PNG,
                    "0"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)

pre = aft = nav = None
for line in (r.stdout or "").splitlines():
    try:
        if line.startswith("BEFORE:"):
            pre = json.loads(line[7:])
        elif line.startswith("AFTER:"):
            aft = json.loads(line[6:])
        elif line.startswith("NAV:"):
            nav = json.loads(line[4:])
    except Exception as e:
        print("  解析失败 line=%r  err=%s" % (line[:220], e))
if not pre or not aft:
    print("--- RAW STDOUT ---")
    for ln in (r.stdout or "").splitlines():
        print("  |" + ln[:160])
    print("--- STDERR ---")
    print((r.stderr or "")[:400])
    sys.exit(1)


def fmt(o, label):
    print("  %s：面板 %d 块　被悬停=第 %s 块" % (label, o["n"],
          (o["hovered"] + 1) if o["hovered"] is not None else "无"))
    for i, p in enumerate(o["panels"]):
        print("    %d）%s　宽高 %.0f×%.0f　opacity %s　transform %s"
              % (i + 1, p["name"], p["w"], p["h"], p["op"], (p["tr"] or "none")[:26]))
        print("        细节层: 拆解 %s　印章 %s　今字 %s　点位 %d 个　href %s"
              % (p["breakOp"], p["sealOp"], p["modernOp"], p["dots"], p["href"]))


fmt(pre, "默认")
fmt(aft, "悬停第 2 块后")
print()
h = aft["hovered"]
if h is not None:
    hp = aft["panels"][h]
    others = [p for i, p in enumerate(aft["panels"]) if i != h]
    pre_hp = pre["panels"][h]
    print("  放大: %.0f×%.0f → %.0f×%.0f（%s）"
          % (pre_hp["w"], pre_hp["h"], hp["w"], hp["h"],
             "已放大" if hp["w"] > pre_hp["w"] + 2 else "未放大 X"))
    print("  其余弱化: %s" % (' '.join(p["op"] for p in others)))
    print("  细节层显现: 拆解 %s→%s　印章 %s→%s　今字 %s→%s"
          % (pre_hp["breakOp"], hp["breakOp"], pre_hp["sealOp"], hp["sealOp"],
             pre_hp["modernOp"], hp["modernOp"]))
    row = aft["row"]
    bottom = max(p["h"] for p in aft["panels"])
    print("  放大后是否被裁: 行高 %d　最高面板 %.0f　%s"
          % (row["h"], bottom,
             "未裁" if row["h"] >= max(p["h"] for p in aft["panels"]) - 1 else "可能被裁 X"))
    print("  是否横向溢出: %s" % ("是 X" if aft["sw"] > aft["docW"] else "无"))
if nav:
    print()
    print("  点击第 3 块 → hash=%s　场景=%s　报错=%s"
          % (nav.get("hash"), nav.get("scene"), nav.get("err")))
print()
print("  截图 %s" % PNG)

child.kill()
for f in (ns,):
    try:
        os.remove(f)
    except OSError:
        pass
