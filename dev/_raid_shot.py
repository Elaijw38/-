# -*- coding: utf-8 -*-
"""构件讨伐：把一条完整的战斗链走一遍，逐步截图。

为什么要走全链：形象崩坏度、命中飘字、结算里的名录面板，都**只在特定战况下**
才出现。单看一张静态截图证明不了"形象真的跟着战斗在变"，所以这里按真实操作
推进——进关 → 拆构件 → 阶段二 → 笔画终局 → 结算——每推进一步截一张，
并把当步的关键量取回来（.bd-figure 的 class、飘字文本、形象 src）。

用法：python dev/_raid_shot.py <关卡序号,0基> <构件,逗号分隔或-> <宽> <高> <输出目录>
例：  python dev/_raid_shot.py 0 水,止 1440 1000 _check/raid
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
NODE = r"C:\Users\32058\.workbuddy\binaries\node\versions\22.22.2-6\node.exe"

IDX = sys.argv[1] if len(sys.argv) > 1 else "0"
COMPS = [x for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else []) if x and x != "-"]
W = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
H = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
OUT = sys.argv[5] if len(sys.argv) > 5 else os.path.join(REPO, "_check", "raid")
if not os.path.isabs(OUT):
    OUT = os.path.join(REPO, OUT)
os.makedirs(OUT, exist_ok=True)

URL = "http://127.0.0.1:8099/index.html#/play/boss-raid"

CDP = r'''
const fs = require('fs');
const path = require('path');
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
/* 页面里抛的异常一律记下来：只靠"某块没渲染出来"倒推是猜谜，
   直接拿到行号与消息才是证据。 */
const ERRS = [];
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.method === 'Runtime.exceptionThrown') {
    const d = (m.params && m.params.exceptionDetails) || {};
    ERRS.push(((d.exception && (d.exception.description || d.exception.value)) || d.text || '?')
      .split('\n').slice(0, 2).join(' | ') + '  @' + (d.lineNumber || 0) + ':' + (d.columnNumber || 0));
  }
  if (m.method === 'Runtime.consoleAPICalled' && m.params && m.params.type === 'error') {
    ERRS.push('console.error: ' + (m.params.args || [])
      .map(a => a.value || a.description || '').join(' ').slice(0, 200));
  }
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
const ev = async (expr) => {
  const a = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  if (a.exceptionDetails) { return 'ERR:' + (a.exceptionDetails.text || ''); }
  return a.result && a.result.value;
};
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const OUTDIR = process.argv[6];
const IDX = +process.argv[7];
const COMPS = (process.argv[8] || '').split(',').filter(Boolean);

/* 每一步都取同一组量：怪像现在的崩坏度、飘字有没有出现、形象是不是本尊的。 */
const STATE = "JSON.stringify((function(){" +
  "var f=document.querySelector('.bd-figure');" +
  "var fx=document.querySelector('.bd-figure-fx');" +
  "var art=document.querySelector('.bd-figure-art');" +
  "var hp=document.querySelector('.bd-hpnum');" +
  "var st=document.querySelector('.bd-progress-value');" +
  "return {" +
  "view:(document.querySelector('.bd-win')?'win':(document.querySelector('.bd-field')?'fight':'-'))," +
  "figClass:f?f.className:'-'," +
  "fxClass:fx?fx.className:'-', fxText:fx?fx.textContent:'-'," +
  "artSrc:art?String(art.getAttribute('src')).split('/').pop():'-'," +
  "artOk:art?(art.complete&&art.naturalWidth>0):false," +
  "artVisible:art?getComputedStyle(art).display!=='none':false," +
  "hp:hp?hp.textContent.trim():'-', prog:st?st.textContent.trim():'-'," +
  "cut:(document.querySelectorAll('.bo-cut').length)," +
  "phase:(document.querySelector('.bd-field.final')?'3':" +
    "(document.querySelector('.bd-field.broken')?'2':'1'))," +
  "winCodex:!!document.querySelector('.bd-wincodex')," +
  "winCodexTxt:document.querySelector('.bd-wincodex')?" +
    /* 别写 /\s+/：这是在 JS 字符串里，\s 会被当成未知转义吃成 s，
       于是 "Boss" 显示成 "Bo"。用字符组最稳。 */
    "document.querySelector('.bd-wincodex').textContent" +
      ".replace(/[ \\n\\r\\t]+/g,' ').slice(0,110):'-'," +
  "overflowX:document.documentElement.scrollWidth-window.innerWidth};})())";

/* 点一个元素。**不能用 el.click()**：SVG 的 <g>（.bo-cut / .bo-part）
   是 SVGElement，没有 HTMLElement 的 click()——调它会抛 TypeError，
   而异常被 ev() 吞掉之后表现得就像"点了没反应"，很容易误判成游戏坏了。 */
const fire = (sel) => ev("(function(){var c=document.querySelector('" + sel + "');" +
  "if(!c)return 'none';c.dispatchEvent(new MouseEvent('click'," +
  "{bubbles:true,cancelable:true,view:window}));return 'ok';})()");

const shots = [];
async function shot(name) {
  const v = await ev(STATE);
  const s = await send('Page.captureScreenshot', {format: 'png'});
  fs.writeFileSync(path.join(OUTDIR, name), Buffer.from(s.data, 'base64'));
  shots.push({name: name, state: v});
}
/* 按元素实际位置裁一张放大的局部。全页截图缩到 1080 宽之后，
   尺寸只有 100px 上下的怪像基本看不清；而"形象到底读不读得出来"
   恰恰是这一步要看的，所以必须按 DOM 的 rect 精确裁，不靠人眼估坐标。 */
async function shotEl(name, sel, scale) {
  const r = await ev("(function(){var e=document.querySelector('" + sel + "');" +
    "if(!e)return '';var b=e.getBoundingClientRect();" +
    "return JSON.stringify({x:b.x,y:b.y,width:b.width,height:b.height});})()");
  if (!r || typeof r !== 'string' || r[0] !== '{') { return; }
  const b = JSON.parse(r);
  const pad = 8;
  const s = await send('Page.captureScreenshot', {format: 'png', clip: {
    x: Math.max(0, b.x - pad), y: Math.max(0, b.y - pad),
    width: b.width + pad * 2, height: b.height + pad * 2,
    scale: scale || 2}});
  fs.writeFileSync(path.join(OUTDIR, name), Buffer.from(s.data, 'base64'));
}

ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1,
     mobile: +process.argv[3] < 700});
  await send('Page.navigate', {url: process.argv[5]});
  await wait(5200);

  await shot('00-track.png');
  /* 讨伐榜的"悬停换怪"：指针落到某一关，左边那一尊应换成**这一关自己要打的**。
     量的是 band 里那张图的 src——默认应是本阶通则图，悬停后应是这一关的专属图。 */
  const artBefore = await ev("(function(){var i=document.querySelector('.bo-tier-img');" +
    "return i?i.getAttribute('src'):'-';})()");
  await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + IDX +
    "];if(!b)return 'none';" +
    "b.dispatchEvent(new PointerEvent('pointerenter',{bubbles:false}));return 'ok';})()");
  await wait(700);
  const artAfter = await ev("(function(){var i=document.querySelector('.bo-tier-img');" +
    "return i?i.getAttribute('src'):'-';})()");
  const artName = await ev("(function(){var n=document.querySelector('.bo-tier-artname');" +
    "return n?n.textContent:'-';})()");
  console.log('HOVER:' + JSON.stringify({before: artBefore, after: artAfter, name: artName}));
  await shot('00b-track-hover.png');
  await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + IDX +
    "];if(b)b.dispatchEvent(new PointerEvent('pointerleave',{bubbles:false}));return 'ok';})()");
  await wait(400);

  await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + IDX +
    "];if(b&&!b.disabled)b.click();return !!b;})()");
  await wait(1700);
  await shot('01-fight.png');
  await shotEl('01-fight-fig.png', '.bd-figure', 2.4);

  /* 一次拆一块正确的构件：看得见"这一手落在它身上" */
  for (var i = 0; i < COMPS.length; i++) {
    await ev("(function(){var c=document.querySelector('.bd-chip[aria-label=\"构件 " + COMPS[i] +
      "\"]');if(c&&!c.disabled)c.click();return !!c;})()");
    /* 先抢一张"飘字还在飞"的：动画 0.95s，等满再截就只剩一个快淡没的残影，
       证明不了"这一手报出来了"。 */
    await wait(300);
    await shotEl('02-break' + (i + 1) + '-fx.png', '.bd-figure', 2.4);
    await wait(650);
    await shot('02-break' + (i + 1) + '.png');
    await shotEl('02-break' + (i + 1) + '-fig.png', '.bd-figure', 2.4);
    if (i + 1 < COMPS.length) { await wait(1400); }
  }

  /* 阶段一转阶段二：构件崩坏 */
  await wait(1200);
  await shot('03-phase2.png');
  await shotEl('03-phase2-fig.png', '.bd-figure', 2.4);

  /* 和龟宝改用笔画。按钮已从 .bd-actions 搬到提示卡正文下面
     （.bd-guide-btn），池子那条细栏里也有一份（.bd-pool-cta）。
     两个都试，取先命中的那个。 */
  await ev("(function(){var sels=['.bd-guide-btn','.bd-pool-cta'," +
    "'.bd-actions .btn'];for(var i=0;i<sels.length;i++){" +
    "var b=document.querySelector(sels[i]);" +
    "if(b&&!b.disabled){b.click();return 'hit:'+sels[i];}}return 'none';})()");
  await wait(1500);
  await shot('04-phase3.png');
  await shotEl('04-phase3-fig.png', '.bd-figure', 2.4);

  /* 逐段斩。斩到近半时形象会"剥落到只剩纹路"，那一度单截一张。 */
  const total = +((await ev("document.querySelectorAll('.bo-cut').length")) || 0);
  const half = Math.max(1, Math.floor(total / 2));
  for (var k = 0; k < half; k++) {
    await fire('.bo-cut');
    await wait(620);
  }
  await shot('05-stripped.png');
  await shotEl('05-stripped-fig.png', '.bd-figure', 2.4);
  for (var m = 0; m < 40; m++) {
    const left = await ev("document.querySelectorAll('.bo-cut').length");
    if (!left || left === 'ERR:') { break; }
    await fire('.bo-cut');
    await wait(520);
  }
  await wait(1400);
  await shot('06-win.png');
  await shotEl('06-win-fig.png', '.bd-winfig', 1.8);
  await shotEl('06-win-codex.png', '.bd-wincodex', 2);

  console.log('SHOTS:' + JSON.stringify(shots));
  console.log('ERRS:' + JSON.stringify(ERRS.slice(0, 6)));
  try { await send('Browser.close'); } catch (e) {}
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_raid.js")
io.open(ns, "w", encoding="utf-8").write(CDP)


def probe(run_no):
    port = 9950 + ((os.getpid() + run_no * 41) % 40)
    prof = os.path.join(OUT, "raidprof-%d-%d" % (int(time.time()), run_no))
    subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
    child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                              "--remote-debugging-port=%d" % port, "--user-data-dir=" + prof,
                              "--window-size=1200,900", "about:blank"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    targets = None
    for _ in range(70):
        time.sleep(0.4)
        try:
            targets = json.load(urllib.request.urlopen(
                "http://127.0.0.1:%d/json/list" % port, timeout=10))
            if any(t.get("type") == "page" and t.get("webSocketDebuggerUrl") for t in targets):
                break
        except Exception:
            pass
    pages = [t for t in (targets or [])
             if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not pages:
        child.kill()
        return None, "", "没有拿到可调试的 page target"
    r = subprocess.run([NODE, ns, pages[0]["webSocketDebuggerUrl"], str(W), str(H),
                        URL, OUT, IDX, ",".join(COMPS)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=400)
    child.kill()
    shots = None
    errs = []
    for line in (r.stdout or "").splitlines():
        if line.startswith("SHOTS:"):
            shots = json.loads(line[6:])
        if line.startswith("ERRS:"):
            errs = json.loads(line[5:])
        if line.startswith("HOVER:"):
            h = json.loads(line[6:])
            print("讨伐榜悬停换怪：%s → %s（%s）  %s"
                  % (h["before"], h["after"], h["name"],
                     "✓ 换成了这一关的怪" if h["before"] != h["after"] else "！没换"))
    for e in errs:
        print("   页面异常: " + e)
    return shots, r.stdout or "", r.stderr or ""


shots, out, err = None, "", ""
for attempt in (1, 2):
    shots, out, err = probe(attempt)
    if shots:
        break
    print("   ！第 %d 次没拿到结果，重试" % attempt)
    time.sleep(1.0)

if not shots:
    print("!! 未取到 SHOTS")
    print("stdout:", out[:700])
    if err:
        print("stderr:", err[:400])
else:
    for s in shots:
        st = s["state"]
        # 页面那边交回来的是 JSON.stringify 的**字符串**，不是对象；
        # 这里不先 loads 一下，每一条都会走进"探针没取到状态"的分支——
        # 而数据其实是好的。这种假警报最坏：真正取不到时反而看不出来。
        if isinstance(st, str) and st.lstrip().startswith("{"):
            try:
                st = json.loads(st)
            except ValueError:
                st = None
        if not isinstance(st, dict):
            print("%-16s ！！探针没取到状态：%s" % (s["name"], str(st)[:300]))
            continue
        print("%-16s view=%-4s phase=%s  fig=%-22s art=%-16s ok=%s"
              % (s["name"], st["view"], st["phase"], st["figClass"],
                 st["artSrc"], st["artOk"]))
        print("%18s %s  %s  飘字=%r%s"
              % ("", st["hp"], st["prog"], st["fxText"],
                 ("  名录面板=" + st["winCodexTxt"]) if st["winCodex"] else ""))
        if st["overflowX"]:
            print("%18s ！横向溢出 %dpx" % ("", st["overflowX"]))
print("输出目录 %s" % OUT)
try:
    os.remove(ns)
except OSError:
    pass
