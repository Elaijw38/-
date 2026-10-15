# -*- coding: utf-8 -*-
"""构件池收窄 + "改用笔画"入口位置：验证工具。

两件事都是**行为**，不是一张静态图能证明的：

  ① 池子收窄到 12 个之后，正确项是不是**一次都没漏**。
     漏一个 = 这一关直接打不过去。所以要反复进关（每次重抽），
     逐关核对"池子里有没有本关的全部构件"，以及池子大小是不是恒定
     （大小一变，看池子就能反推答案有几个）。
  ② "改用笔画"搬进提示卡之后，是不是真的在**首屏可见、且点得到**。
     原先它挂在页面最底部的操作行、构件池下面，被推到屏幕之外，
     这是玩家反馈"不太好发现"的根因。所以这里量三个数：
     按钮矩形、视口高度、以及 elementFromPoint 命中测试
     （命中测试能区分"在视口里"和"真没被挡住"）。

用法：python dev/_pool_test.py [重复次数] [宽] [高]
例：  python dev/_pool_test.py 6 1440 1000
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

REPEAT = int(sys.argv[1]) if len(sys.argv) > 1 else 6
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1440
H = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
OUT = os.path.join(REPO, "_check")
os.makedirs(OUT, exist_ok=True)
URL = "http://127.0.0.1:8099/index.html#/play/boss-raid"

CDP = r'''
/* 这个脚本里有顶层 await，Node 会把它按 ESM 跑——
   所以不能用 require()，两者同时出现会直接报
   ERR_AMBIGUOUS_MODULE_SYNTAX。用 import。 */
import { writeFileSync } from 'node:fs';
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
const ERRS = [];
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.method === 'Runtime.exceptionThrown') {
    const d = (m.params && m.params.exceptionDetails) || {};
    ERRS.push(((d.exception && (d.exception.description || d.exception.value)) || d.text || '?')
      .split('\n').slice(0, 2).join(' | '));
  }
  if (m.method === 'Runtime.consoleAPICalled' && m.params && m.params.type === 'error') {
    ERRS.push('console.error: ' + (m.params.args || [])
      .map(a => a.value || a.description || '').join(' ').slice(0, 200));
  }
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
const ev = async (expr) => {
  const a = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  if (a.exceptionDetails) {
    /* 只取 text 会得到一句没有信息量的 "Uncaught"。真正的消息在
       exceptionDetails.exception.description 里，必须一起带出来。 */
    const d = a.exceptionDetails;
    return 'ERR:' + String(d.text || '') + ' ' +
      String((d.exception && (d.exception.description || d.exception.value)) || '')
        .split('\n')[0];
  }
  return a.result && a.result.value;
};
const wait = (ms) => new Promise(r => setTimeout(r, ms));
/* 轮询到某个条件成立为止。固定 sleep 在这里很脆：进关要重建整片战场，
   快慢随机器变，睡短了会读到一个空的池子（然后误判成"池子没铺"）。 */
const waitFor = async (expr, ms) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await ev(expr) === true) { return true; }
    await wait(150);
  }
  return false;
};
const REPEAT = +process.argv[4];
const OUTDIR = process.argv[5];

/* 截一个元素。用它的矩形当 clip 并允许超出视口——
   池子在首屏之下，用整屏截图根本看不到，也就没法判断
   "12 个铺成几行、长什么样"。 */
const shotEl = async (file, sel, scale) => {
  const r = await ev("JSON.stringify((function(){var e=document.querySelector('" + sel + "');" +
    "if(!e)return null;var b=e.getBoundingClientRect();" +
    "return {x:b.left,y:b.top,w:b.width,h:b.height};})())");
  if (typeof r !== 'string' || r.indexOf('{') !== 0) { return false; }
  const b = JSON.parse(r);
  if (!b || !b.w || !b.h) { return false; }
  const s = await send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true,
    clip: {x: b.x, y: b.y, width: b.w, height: b.h, scale: scale || 1}});
  if (s && s.data) { writeFileSync(file, Buffer.from(s.data, 'base64')); return true; }
  return false;
};

/* WebSocket 连上之前发消息会直接抛 InvalidStateError。
   先等 open；已经 open 了就别等（那一次 open 事件已经过去了，再等会永久挂住）。 */
if (ws.readyState !== 1) {
  await new Promise(r => ws.addEventListener('open', r, {once: true}));
}

/* 页面里的关卡表，与 boss-raid.js 的 levelList() 同一构造顺序（阶→关） */
const LEVELS = "(function(){var o=[];var T=App.levels.boss.tiers||[];" +
  "for(var i=0;i<T.length;i++){var L=T[i].list||[];" +
  "for(var j=0;j<L.length;j++)o.push({idx:o.length,tier:T[i].id,char:L[j].char,comps:L[j].comps||[]});}" +
  "return o;})()";

await send('Runtime.enable');
await send('Page.enable');

/* 新开的 Edge 停在 about:blank，必须显式导航——否则每一条 evaluate 都是
   "App is not defined"，而 ev() 只回一个 'ERR:' 字符串，看起来像数据不对。 */
await send('Page.navigate', {url: process.argv[3]});
/* 就绪判据用真实数据在不在，而不是睡固定时长。 */
const ready = async (ms) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await ev("!!(window.App&&App.levels&&App.levels.boss&&App.levels.boss.tiers)") === true) { return true; }
    await wait(200);
  }
  return false;
};
if (!await ready(20000)) { console.log('ERRS:["页面 20s 内没起来"]'); process.exit(1); }

/* 全部解锁：第 7 关以后默认是关着的，不解锁进不去。
   注意键名——App.store 内部会自己加 'ziqu.' 前缀（storeKey()），
   这里写 'ziqu.bossraid' 会存成 ziqu.ziqu.bossraid，等于没写：
   症状是"只有第 1 关进得去，其余全卡在 locked"，很难看出是键的问题。 */
await ev("App.store.set('bossraid',{cleared:[" +
  "0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],perfect:[]});'ok'");
await send('Page.reload', {ignoreCache: true});
if (!await ready(20000)) { console.log('ERRS:["重载后页面没起来"]'); process.exit(1); }
await wait(700);

const lvsRaw = await ev("JSON.stringify(" + LEVELS + ")");
if (typeof lvsRaw !== 'string' || lvsRaw.indexOf('[') !== 0) {
  console.log('ERRS:' + JSON.stringify(['关卡表取不到: ' + lvsRaw]));
  process.exit(1);
}
const LVS = JSON.parse(lvsRaw);

/* 只测有构件池的那 6 关（合体 BOSS）；其余 15 关没有池子 */
const POOL_LVS = LVS.filter(function (l) { return l.comps.length > 0; });
console.log('POOLLEVELS:' + JSON.stringify(POOL_LVS.map(function (l) {
  return { idx: l.idx, char: l.char, comps: l.comps }; })));

/* —— ① 反复进关，核对池子 —— */
const rows = [];
for (let r = 0; r < REPEAT; r++) {
  for (const lv of POOL_LVS) {
    /* 回到关卡榜 */
    await ev("(function(){var b=[].slice.call(document.querySelectorAll('.bd-hud .btn'))" +
      ".filter(function(x){return x.textContent.indexOf('关卡')>=0;})[0];" +
      "if(b)b.click();return !!b;})()");
    await waitFor("!!document.querySelector('.bo-board .bo-bead')", 8000);
    const hit = await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + lv.idx +
      "];if(b&&!b.disabled){b.click();return 'ok';}return 'locked';})()");
    /* 等这一关真的立起来——判据是构件池铺出来了，而不是睡够多少毫秒 */
    const up = await waitFor("document.querySelectorAll('.bd-chip').length>0", 10000);
    if (!up) {
      rows.push({ round: r + 1, idx: lv.idx, char: lv.char, seen: '', click: hit, n: 0,
                  alive: 0, names: [], miss: ['本关没立起来'], dup: false, all: lv.comps });
      continue;
    }
    const st = await ev("JSON.stringify((function(){" +
      "var cs=[].slice.call(document.querySelectorAll('.bd-chip'));" +
      "return {" +
      "char:(function(){var e=document.querySelector('.bd-side-name .bo-spoiler-a');" +
        "return e?e.textContent:'';})()," +
      "n:cs.length," +
      "alive:cs.filter(function(c){return !c.disabled;}).length," +
      "names:cs.map(function(c){return (c.getAttribute('aria-label')||'').replace('构件 ','');})" +
      "};})())");
    if (typeof st !== 'string' || st.indexOf('{') !== 0) {
      rows.push({ round: r + 1, idx: lv.idx, char: lv.char, n: -1, names: [],
                  miss: ['PROBE:' + String(st).slice(0, 80)] });
      continue;
    }
    const o = JSON.parse(st);
    const missing = lv.comps.filter(function (c) { return o.names.indexOf(c) < 0; });
    const dup = o.names.length !== new Set(o.names).size;
    rows.push({ round: r + 1, idx: lv.idx, char: lv.char, seen: o.char, click: hit,
                n: o.n, alive: o.alive, names: o.names, miss: missing, dup: dup, all: lv.comps });
  }
}
console.log('ROWS:' + JSON.stringify(rows));

/* —— ② 阶段二：入口按钮在不在首屏、点不点得到 —— */
await ev("(function(){var b=[].slice.call(document.querySelectorAll('.bd-hud .btn'))" +
  ".filter(function(x){return x.textContent.indexOf('关卡')>=0;})[0];if(b)b.click();return !!b;})()");
await waitFor("!!document.querySelector('.bo-board .bo-bead')", 8000);
await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[0];" +
  "if(b&&!b.disabled)b.click();return !!b;})()");
await waitFor("document.querySelectorAll('.bd-chip').length>0", 10000);

/* —— 阶段一：收窄后的池子铺成几行、占多高 —— */
const p1 = await ev("JSON.stringify((function(){" +
  "window.scrollTo(0,0);" +
  "function R(s){var e=document.querySelector(s);if(!e)return null;" +
    "var r=e.getBoundingClientRect();return {t:Math.round(r.top),b:Math.round(r.bottom)," +
    "h:Math.round(r.height),w:Math.round(r.width)};}" +
  "var chips=[].slice.call(document.querySelectorAll('.bd-chip'));" +
  "var tops=[];" +
  "chips.forEach(function(c){var t=Math.round(c.getBoundingClientRect().top);" +
    "if(tops.indexOf(t)<0)tops.push(t);});" +
  "return {n:chips.length," +
  "chipW:chips.length?Math.round(chips[0].getBoundingClientRect().width):0," +
  "chipH:chips.length?Math.round(chips[0].getBoundingClientRect().height):0," +
  "rows:tops.length, vh:window.innerHeight," +
  "docH:document.documentElement.scrollHeight," +
  "pool:R('.bd-pool'), grid:R('.bd-poolgrid')," +
  "field:R('.bd-field')};})())");
console.log('P1:' + p1);
await shotEl(OUTDIR + '/pool-phase1.png', '.bd-pool', 1.5);
await shotEl(OUTDIR + '/guide-phase1.png', '.bd-field-guide', 1.5);

for (const c of POOL_LVS[0].comps) {
  await ev("(function(){var c=document.querySelector('.bd-chip[aria-label=\"构件 " + c +
    "\"]');if(c&&!c.disabled)c.click();return !!c;})()");
  await wait(600);
}
const gotP2 = await waitFor("!!document.querySelector('.bd-guide-btn')", 12000);
console.log('GOTP2:' + gotP2);
await shotEl(OUTDIR + '/guide-phase2.png', '.bd-field-guide', 1.5);
await shotEl(OUTDIR + '/pool-phase2.png', '.bd-pool', 1.5);
await shotEl(OUTDIR + '/field-phase2.png', '.bd-field', 1);

const p2 = await ev("JSON.stringify((function(){" +
  "window.scrollTo(0,0);" +
  "function R(s){var e=document.querySelector(s);if(!e)return null;" +
    "var r=e.getBoundingClientRect();return {t:Math.round(r.top),b:Math.round(r.bottom)," +
    "l:Math.round(r.left),w:Math.round(r.width),h:Math.round(r.height)};}" +
  "var btn=document.querySelector('.bd-guide-btn');" +
  "var hit=false;" +
  "if(btn){var r=btn.getBoundingClientRect();var el=document.elementFromPoint(" +
    "r.left+r.width/2, r.top+r.height/2);hit=!!(el&&(el===btn||btn.contains(el)));}" +
  "return {" +
  "phase:(function(){var e=document.querySelector('.bd-phase.on');return e?e.textContent.trim():'-';})()," +
  "vh:window.innerHeight," +
  "guideBtn:!!btn, btnText:btn?btn.textContent.trim():'-'," +
  "btnRect:R('.bd-guide-btn'), hitTest:hit," +
  "poolDead:!!document.querySelector('.bd-pool.is-dead')," +
  "chipsNow:document.querySelectorAll('.bd-chip').length," +
  "poolRect:R('.bd-pool'), poolCta:!!document.querySelector('.bd-pool-cta')," +
  /* 注意：这里的字符串最终会被 **Node 先解析一次**，再交给浏览器解析。
     所以写 /[ \n\r\t]+/g 是错的——\n 在这一层就被吃成真正的换行，
     浏览器拿到的正则跨了行，报 "Invalid regular expression: missing /"。
     这种错很难从"探针没取到值"里看出来，索性不用正则：
     把原文带回去，在 Python 里用 str.split() 归一。 */
  "actionsText:(function(){var a=document.querySelector('.bd-actions');" +
    "return a?a.textContent:'-';})()," +
  "actionsHasStroke:(function(){var a=document.querySelector('.bd-actions');" +
    "return a?a.textContent.indexOf('笔画')>=0:false;})()," +
  "fieldRect:R('.bd-field')" +
  "};})())");
console.log('P2:' + p2);

/* 按钮真的点得动吗 */
const clicked = await ev("(function(){var b=document.querySelector('.bd-guide-btn');" +
  "if(!b)return 'none';b.click();return 'ok';})()");
await wait(800);
const p3 = await ev("JSON.stringify((function(){" +
  "return {" +
  "phase:(function(){var e=document.querySelector('.bd-phase.on');return e?e.textContent.trim():'-';})()," +
  "cuts:document.querySelectorAll('.bo-cut').length," +
  "poolDead:!!document.querySelector('.bd-pool.is-dead')," +
  "poolCta:!!document.querySelector('.bd-pool-cta')," +
  "chipsNow:document.querySelectorAll('.bd-chip').length};})())");
console.log('P3:' + p3);
console.log('CLICKED:' + clicked);
console.log('ERRS:' + JSON.stringify(ERRS));
ws.close(); process.exit(0);
'''

ns = os.path.join(REPO, "_cdp_pool.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9871
prof = os.path.join(OUT, "poolprof")
subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
child = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port, "--user-data-dir=" + prof,
                          "--window-size=%d,%d" % (W, H), "about:blank"],
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], URL, str(REPEAT), OUT],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
try:
    subprocess.run(["cmd", "/c", "taskkill", "/f", "/pid", str(child.pid)], capture_output=True)
except Exception:
    pass

lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
if r.returncode != 0 or not lines:
    print("CDP 失败。stdout/stderr:")
    print(r.stdout)
    print(r.stderr[-2000:])
    sys.exit(1)

pool_lvs = rows = p2 = p3 = errs = None


def take(prefix):
    """取值。解析不动就把原文带回来——不然只能看到一个空的 JSONDecodeError，
       无从判断是"页面没到那一步"还是"探针写错了"。"""
    for l in lines:
        if l.startswith(prefix):
            raw = l[len(prefix):]
            try:
                return json.loads(raw)
            except Exception:
                return {"_raw": raw[:400]}
    return {"_raw": "(这一行没出现)"}


pool_lvs = take("POOLLEVELS:")
rows = take("ROWS:")
p1raw = take("P1:")
p1 = p1raw if isinstance(p1raw, dict) and "_raw" not in p1raw else {}
p2 = take("P2:")
p3 = take("P3:")
errs = take("ERRS:")
clicked = take("CLICKED:")
if isinstance(rows, dict):
    rows = []
if not isinstance(pool_lvs, list):
    pool_lvs = []

print("=" * 68)
print("构件池收窄 + 改用笔画入口  验证")
print("=" * 68)
print("有构件池的关（合体 BOSS）：%d 关" % len(pool_lvs or []))
for l in (pool_lvs or []):
    print("   #%d %s  正确构件 %s" % (l["idx"] + 1, l["char"], "·".join(l["comps"])))

rows = rows or []
sizes = sorted(set(x["n"] for x in rows))
print("\n① 反复进关 %d 轮 × %d 关 = %d 次" % (REPEAT, len(pool_lvs or []), len(rows)))
print("   池子大小出现的值：%s   （应当只有一个数）" % sizes)
bad_miss = [x for x in rows if x["miss"]]
bad_dup = [x for x in rows if x.get("dup")]
bad_size = [x for x in rows if x["n"] != sizes[0]] if sizes else []
print("   漏掉正确项：%d 次 %s" % (len(bad_miss), [x["char"] for x in bad_miss[:8]]))
print("   池内重复　：%d 次" % len(bad_dup))
print("   大小异常　：%d 次" % len(bad_size))
distinct = {}
for x in rows:
    nm = [n for n in (x.get("names") or []) if isinstance(n, str)]
    distinct.setdefault(x["char"], set()).add("|".join(sorted(nm)))
print("   每关候选组合互不相同（重抽有效）：")
for ch, s in distinct.items():
    print("      %s  出现 %d 种不同组合" % (ch, len(s)))

# 逐行摊开：只看汇总数字分不清"是池子错了"还是"根本没进到那一关"。
# 所以把"期望进哪一关"和"页面实际报出的字"并排打出来。
print("\n   逐次明细（轮 / 关序 / 期望字 / 页面实际字 / 池子大小 / 漏掉的构件）")
for x in rows:
    print("      %s  #%-2s 期望 %s  实际 %s  点击 %s  池 %s  漏 %s"
          % (str(x.get("round")), x["idx"] + 1, x["char"], x.get("seen") or "?",
             x.get("click") or "?", x["n"], "·".join(x["miss"]) if x["miss"] else "无"))

print("\n② 阶段一：收窄后的池子长什么样")
if p1:
    pr = p1.get("pool") or {}
    gr = p1.get("grid") or {}
    print("   候选块 %s 个　每个 %s×%s px　铺成 %s 行"
          % (p1.get("n"), p1.get("chipW"), p1.get("chipH"), p1.get("rows")))
    print("   池子框 高 %spx　top=%s　（视口高 %s，整页高 %s）"
          % (pr.get("h"), pr.get("t"), p1.get("vh"), p1.get("docH")))
    print("   候选网格 高 %spx" % gr.get("h"))
else:
    print("   [P1 探针没取到值] %s" % p1)

print("\n③ 阶段二：入口按钮在不在首屏、点不点得到")
p2 = p2 or {}
br = p2.get("btnRect") or {}
print("   当前阶段：%s" % p2.get("phase"))
print("   提示卡按钮 .bd-guide-btn：%s  「%s」" % (p2.get("guideBtn"), p2.get("btnText")))
if br:
    print("      矩形 top=%s bottom=%s 高=%s　视口高=%s" % (br.get("t"), br.get("b"), br.get("h"), p2.get("vh")))
    print("      首屏完整可见（bottom ≤ 视口高）：%s" % (br.get("b", 999) <= p2.get("vh", 0)))
print("      elementFromPoint 命中按钮本身（真没被挡）：%s" % p2.get("hitTest"))
print("   构件池已收窄成一条细栏 .bd-pool.is-dead：%s" % p2.get("poolDead"))
print("   池子里残留的构件块 .bd-chip：%s 个" % p2.get("chipsNow"))
print("   细栏里也带一个入口 .bd-pool-cta：%s" % p2.get("poolCta"))
print("   页面底部操作行内容：「%s」　还夹着笔画按钮吗：%s"
      % (" ".join(str(p2.get("actionsText") or "").split()), p2.get("actionsHasStroke")))

p3 = p3 or {}
print("\n④ 点下去之后")
print("   阶段推进到：%s　可斩笔画 .bo-cut=%s 段" % (p3.get("phase"), p3.get("cuts")))
print("   池子仍为细栏：%s　细栏入口已收起：%s　残余构件块：%s"
      % (p3.get("poolDead"), not p3.get("poolCta"), p3.get("chipsNow")))

print("\n⑤ 控制台异常：%s" % ("无" if not errs else errs))
print("   按钮点击结果：%s" % clicked)
print("   截图：%s/pool-phase1.png　guide-phase1.png　guide-phase2.png　pool-phase2.png"
      % OUT)
for tag, v in (("POOLLEVELS", pool_lvs), ("P1", p1raw), ("P2", p2), ("P3", p3)):
    if isinstance(v, dict) and "_raw" in v:
        print("   [%s 探针没取到值] %s" % (tag, v["_raw"]))
