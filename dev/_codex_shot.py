# -*- coding: utf-8 -*-
"""讨伐名录专项验证截图（CDP 真视口）。

比对的对象是**渲染结果**，不是源码：图鉴里那 88 尊 Boss 形象到底有没有
真的加载出来、骨胎底色跟 PNG 内填色是否对得上、卡片会不会被挤变形。
所以除了截图，还要把下面这些量取回来：
  · .atlas-card.is-codex 的条数 与 图片 naturalWidth>0 的条数
    （后者才是"真的画出来了"，前者只证明 DOM 建了）
  · .ac-ob 的 computed backgroundColor —— 必须等于资产的 #f7efe1，
    不等就会在剪影外圈露出一圈方框
  · 实际列宽（走 :has() 放宽后有没有生效）
  · 横向溢出

用法：python dev/_codex_shot.py <路由> <宽> <高> <输出png> [滚动到] [点开的字]
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
OUT = os.path.join(REPO, "_check")
os.makedirs(OUT, exist_ok=True)

ROUTE = sys.argv[1] if len(sys.argv) > 1 else "atlas"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1440
H = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
PNG = sys.argv[4] if len(sys.argv) > 4 else os.path.join(OUT, "codex.png")
Y = int(sys.argv[5]) if len(sys.argv) > 5 else 0
CLICK = sys.argv[6] if len(sys.argv) > 6 else ""

URL = "http://127.0.0.1:8099/index.html#/" + ROUTE.lstrip("#/").lstrip("/")

CDP = r'''
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
const ev = async (expr) => {
  const a = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  return a.result && a.result.value;
};
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1,
     mobile: +process.argv[3] < 700});
  await send('Page.navigate', {url: process.argv[5]});
  await new Promise(r => setTimeout(r, 4500));
  const yv = process.argv[7];
  if (yv && +yv > 0) {
    await send('Runtime.evaluate', {expression: 'window.scrollTo(0,' + yv + ')'});
    await new Promise(r => setTimeout(r, 1200));
  } else if (yv && +yv < 0) {
    /* 负数：把名录那一段拖到视口中间。名录排在五组的最末，
       正数要一路猜页高，不如直接定位到元素。 */
    await ev("(function(){var c=document.querySelector('.atlas-card.is-codex');" +
      "if(c)c.scrollIntoView({block:'center'});return 1;})()");
    await new Promise(r => setTimeout(r, 2200));
  }
  const click = process.argv[8] || '';
  if (click) {
    await ev("(function(){var c=[].slice.call(document.querySelectorAll('.atlas-card.is-codex'))" +
      ".filter(function(x){return x.querySelector('.ac-rub').textContent.trim()==='" + click + "';})[0];" +
      "if(c)c.click();return !!c;})()");
    await new Promise(r => setTimeout(r, 2600));
  }
  const expr = "JSON.stringify((function(){var de=document.documentElement;" +
    "var cs=[].slice.call(document.querySelectorAll('.atlas-card.is-codex'));" +
    "var imgs=cs.map(function(c){return c.querySelector('.ac-art');});" +
    "var ok=imgs.filter(function(i){return i&&i.complete&&i.naturalWidth>0;}).length;" +
    "var box=cs.length?cs[0].querySelector('.ac-ob'):null;" +
    "var bcs=box?getComputedStyle(box):null;" +
    "var r=cs.length?cs[0].getBoundingClientRect():null;" +
    "var strip=cs.length?cs[0].closest('.atlas-strip'):null;" +
    "return {" +
    "route:location.hash||''," +
    "codex:cs.length, codexImgOk:ok," +
    "noArt:document.querySelectorAll('.atlas-card.is-codex .ac-ob.no-art').length," +
    "cardW:r?Math.round(r.width):0, cardH:r?Math.round(r.height):0," +
    "obBg:bcs?bcs.backgroundColor:'-', obImg:bcs?bcs.backgroundImage.slice(0,40):'-'," +
    "obPad:bcs?bcs.padding:'-'," +
    "colW:strip?getComputedStyle(strip).gridTemplateColumns.split(' ').length:0," +
    "atlasCards:document.querySelectorAll('.atlas-card').length," +
    "atlasSec:document.querySelectorAll('.atlas-sec').length," +
    "sheetOpen:document.querySelectorAll('#atlasSheet').length," +
    "sheetArt:(function(){var i=document.querySelector('.as-art');" +
      "return i?(i.complete&&i.naturalWidth>0?('ok '+i.naturalWidth+'x'+i.naturalHeight):'BROKEN'):'-';})()," +
    "sheetW:(function(){var b=document.querySelector('.as-left-codex');" +
      "return b?Math.round(b.getBoundingClientRect().width):-1;})()," +
    "overflowX:de.scrollWidth-window.innerWidth, winW:window.innerWidth," +
    /* 卡片高度到底齐不齐，靠眼看截图看不准（骨胎色和纸色太近，
       轮廓大小差异会被误认成框子大小差异）——直接把前 24 张的
       .ac-ob 与 .ac-art 的 rect 量出来，用数据说话。 */
    "rects:cs.slice(0,24).map(function(c){var o=c.querySelector('.ac-ob');" +
      "var i=c.querySelector('.ac-art');var a=o?o.getBoundingClientRect():null;" +
      "var b=i?i.getBoundingClientRect():null;" +
      "return [Math.round(a.width),Math.round(a.height)," +
        "Math.round(b.width),Math.round(b.height)];})," +
    "errors:window.__errs||0};})())";
  const v = await ev(expr);
  console.log('INFO:' + v);
  const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(process.argv[6], Buffer.from(s.data, 'base64'));
  /* 让 Edge 自己退，而不是靠外面 kill：只看 child.kill() 杀不干净，
     下一轮会连到上一轮那个 about:blank 的旧 target，
     症状是"截图空白、route 为空、卡片 0 张"——很像是页面坏了，其实是连错了。 */
  try { await send('Browser.close'); } catch (e) {}
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_codex.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

def probe(run_no):
    """起一个干净的 Edge，跑一次 CDP 探针，返回 (info, stdout, stderr)。

    端口和 profile 每轮都换：端口一旦被上一轮没退干净的实例占住，
    就会连到它那个 about:blank 的旧 target 上——症状是截图空白、
    route 为空、卡片 0 张，看着像页面坏了，其实只是连错了浏览器。
    """
    port = 9800 + ((os.getpid() + run_no * 37) % 150)
    prof = os.path.join(OUT, "codexprof-%d-%d-%d" % (int(time.time()), os.getpid(), run_no))
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
                        URL, PNG, str(Y), CLICK],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=220)
    child.kill()
    info = None
    for line in (r.stdout or "").splitlines():
        if line.startswith("INFO:"):
            info = json.loads(line[5:])
    return info, r.stdout or "", r.stderr or ""


info = None
out, err = "", ""
for attempt in (1, 2):
    info, out, err = probe(attempt)
    # route 为空 = 这一轮其实没进到应用里，别拿一张空页当结论
    if info and info.get("route"):
        break
    print("   ！第 %d 次没进到应用（route 为空），重试" % attempt)
    time.sleep(1.0)
r_out, r_err = out, err
if info:
    print("路由 %s   视口 %dx%d" % (info["route"], W, H))
    print("名录卡片 %d 张；图片真的画出来 %d 张；no-art 兜底 %d 张"
          % (info["codex"], info["codexImgOk"], info["noArt"]))
    print("卡片尺寸 %dx%d   列数 %d   网格列宽 %spx"
          % (info["cardW"], info["cardH"], info["colW"],
             round(info["cardW"], 1) if info["cardW"] else "-"))
    print("骨胎底 computed=%s   padding=%s" % (info["obBg"], info["obPad"]))
    print("   背景图=%r（应为 none）" % info["obImg"])
    print("图鉴总卡片 %d   分组 %d   横向溢出 %dpx（win %d）"
          % (info["atlasCards"], info["atlasSec"], info["overflowX"], info["winW"]))
    rs = info.get("rects") or []
    if rs:
        ow = set(r[0] for r in rs)
        oh = set(r[1] for r in rs)
        aw = set(r[2] for r in rs)
        ah = set(r[3] for r in rs)
        print("前 %d 张 .ac-ob 宽 %s 高 %s    .ac-art 宽 %s 高 %s"
              % (len(rs), sorted(ow), sorted(oh), sorted(aw), sorted(ah)))
        print("   → 骨胎格%s；形象框%s"
              % ("尺寸齐" if len(oh) == 1 else "！尺寸不齐",
                 "尺寸齐" if (len(ah) == 1 and len(aw) == 1) else "！尺寸不齐（contain 会各自留白）"))
    if info["sheetOpen"]:
        print("详情浮层已开：左栏 %dpx   形象 %s" % (info["sheetW"], info["sheetArt"]))
else:
    print("!! 未取到 INFO")
    print("stdout:", r_out[:600])
if r_err:
    print("stderr: " + r_err[:400])
print("截图 %s  %d B" % (PNG, os.path.getsize(PNG) if os.path.exists(PNG) else 0))
try:
    os.remove(ns)
except OSError:
    pass
