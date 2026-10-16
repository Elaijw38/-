# -*- coding: utf-8 -*-
"""第三关 21 关的【形象取用】核验：每一关在**真实战斗界面里**到底渲染的是哪张图。

为什么要专门做这个：形象取用有三个来源——名录专属形象、代用表、本档通用图——
只看 JSON 证明不了浏览器里真的换上了（路径写错、大小写不合、图加载失败都会
静默退化成一张空白或退回通用图）。所以这里逐关真进一次战斗界面，读回：
  ① 讨伐榜悬停时左边那一尊的 src 与名字（选关页也走同一套取用）
  ② 战斗里 .bd-figure-art 的 src、naturalWidth（>0 才算真画出来了）
  ③ .bd-figure-tag 的显示名（代用的应带「· 代用」）
  ④ 结算页是否出现「形象是借的」说明（只有代用关才有）

用法：python dev/_boss_art_check.py [宽] [高] [输出目录]
例：  RAID_URL="file:///C:/.../index.html#/play/boss-raid" python dev/_boss_art_check.py 1440 1000 out/artcheck
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.workbuddy\binaries\node\versions\22.22.2-6\node.exe"

W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
H = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(REPO, "out", "artcheck")
if not os.path.isabs(OUT):
    OUT = os.path.join(REPO, OUT)
os.makedirs(OUT, exist_ok=True)

URL = os.environ.get("RAID_URL") or "http://127.0.0.1:8099/index.html#/play/boss-raid"

CDP = r'''
const fs = require('fs');
const path = require('path');
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
      .split('\n').slice(0, 2).join(' | ') + '  @' + (d.lineNumber || 0) + ':' + (d.columnNumber || 0));
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
const W = +process.argv[3], H = +process.argv[4];
/* 只跑前 N 关：调版面时要在五六个视口高度上反复量，跑满 21 关太慢。
   0 或未给 = 全跑。 */
const MAXLV = +(process.argv[10] || 0);

/* 讨伐榜上左边那一尊现在的样子。
   必须**按悬停那颗珠子所在的档位栏**去取：querySelector('.bo-tier-img')
   永远返回文档里第一个（一阶那一栏）的图，于是二/三阶全被读成
   boss-01-grunt.png，看着像"悬停换怪坏了"，其实是取错了栏。 */
const TRACK = (i) => "JSON.stringify((function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + i +
  "];var s=b?b.closest('.bo-tier'):null;" +
  "var i2=s?s.querySelector('.bo-tier-img'):null;" +
  "var n=s?s.querySelector('.bo-tier-artname'):null;" +
  "var band=s?s.className:'-';" +
  "return {src:i2?String(i2.getAttribute('src')).split('/').pop():'-'," +
  "ok:i2?(i2.complete&&i2.naturalWidth>0):false," +
  "name:n?n.textContent:'-', band:band};})())";
/* 战斗台里的怪像 + 版面量测。
   换形象最容易出的三个事故：①图没加载（静默退回 .no-art）；
   ②图的宽高比与原来那套不同，撑破或缩没了它那一格；③压到字形上。
   三个都直接量，不靠眼看缩略图。 */
const FIGHT = "JSON.stringify((function(){" +
  "function box(e){if(!e)return null;var b=e.getBoundingClientRect();" +
  "return {x:Math.round(b.x),y:Math.round(b.y),w:Math.round(b.width),h:Math.round(b.height)};}" +
  "var a=document.querySelector('.bd-figure-art');" +
  "var t=document.querySelector('.bd-figure-tag');" +
  "var f=document.querySelector('.bd-figure');" +
  "var media=document.querySelector('.bd-figure-media');" +
  "var plate=document.querySelector('.bd-plate');" +
  "var pool=document.querySelector('.bd-pool');" +
  "var bub=document.querySelector('.bd-hero-bubble');" +
  "var phead=document.querySelector('.bd-player-head');" +
  "var ab=box(a), mb=box(media), pb=box(plate), bb=box(bub), phb=box(phead);" +
  "var hp=document.querySelector('.bd-hpnum');" +
  "return {src:a?String(a.getAttribute('src')).split('/').pop():'-'," +
  "ok:a?(a.complete&&a.naturalWidth>0):false," +
  "nw:a?a.naturalWidth:0, nh:a?a.naturalHeight:0," +
  "tag:t?t.textContent:'-', figClass:f?f.className:'-'," +
  "artBox:ab, mediaBox:mb, plateBox:pb," +
  /* 图是否真的落在给它的那一格内（object-fit:contain 之后仍可能被裁） */
  "artInFrame:(ab&&mb)?(ab.h<=mb.h+2&&ab.w<=mb.w+2):null," +
  /* 图与字形是否相交 */
  "artOverGlyph:(ab&&pb)?!(ab.x+ab.w<=pb.x||pb.x+pb.w<=ab.x||" +
    "ab.y+ab.h<=pb.y||pb.y+pb.h<=ab.y):null," +
  "bubble:bub?bub.textContent:'-', bubbleBox:bb," +
  "bubbleOverHead:!!(bb&&phb&&bb.y<phb.y+phb.h&&bb.y+bb.h>phb.y)," +
  "chipN:document.querySelectorAll('.bd-chip').length," +
  "hp:hp?hp.textContent.trim():'-'," +
  "poolBox:box(pool)," +
  /* 真正要落在首屏里的不是池子那个盒子，是**构件的格子**——池子底下那点
     内边距出屏无所谓，格子出屏就得先滚一屏才点得到。所以单独量首尾两格。 */
  "chipBoxes:(function(){var c=document.querySelectorAll('.bd-chip');" +
    "if(!c.length)return null;var t=1e9,bo=-1e9;" +
    "for(var k=0;k<c.length;k++){var r=c[k].getBoundingClientRect();" +
    "t=Math.min(t,r.top);bo=Math.max(bo,r.bottom);}" +
    "return {top:Math.round(t),bot:Math.round(bo),n:c.length};})()," +
  "poolInView:(function(){if(!pool)return null;var b=pool.getBoundingClientRect();" +
    "return b.top>0&&b.top<window.innerHeight;})()" +
  ",overflowX:document.documentElement.scrollWidth-window.innerWidth};})())";

/* 竖排空间明细：池子为什么会掉到首屏外，得先看清上面每一块各占多少。
   只对第 0 关打一次，用来定位（不是每关都要）。 */
const BOXES = "JSON.stringify((function(){" +
  "function b(sel){var e=document.querySelector(sel);if(!e)return null;" +
  "var r=e.getBoundingClientRect();" +
  "return {top:Math.round(r.top),bot:Math.round(r.bottom),h:Math.round(r.height)};}" +
  "return {innerH:window.innerHeight, pageH:document.documentElement.scrollHeight," +
  "head:b('header.top')||b('.top'), bar:b('.play-bar')," +
  "hud:b('.bd-hud'), hudL:b('.bd-hud-left'), hudR:b('.bd-hud-right')," +
  "hudKids:(function(){var e=document.querySelector('.bd-hud');if(!e)return [];" +
  "var o=[];for(var i=0;i<e.children.length;i++){var k=e.children[i];" +
  "var r=k.getBoundingClientRect();var c=getComputedStyle(k);" +
  "o.push({cls:String(k.className).slice(0,24),top:Math.round(r.top),bot:Math.round(r.bottom),h:Math.round(r.height)," +
  "disp:c.display,mt:c.marginTop,mb:c.marginBottom,pt:c.paddingTop,pb:c.paddingBottom});}return o;})()," +
  "wrap:b('.wrap')||b('.play-wrap')||b('main')," +
  "kicker:b('.bd-kicker')||b('.bd-head'), pills:b('.bd-phases')||b('.bd-steps')," +
  "field:b('.bd-field'), hero:b('.bd-hero'), guide:b('.bd-field-guide')," +
  "heroHead:b('.bd-player-head'), portrait:b('.bd-hero-portrait')," +
  "progress:b('.bd-player-progress'), bubble:b('.bd-hero-bubble')," +
  "figure:b('.bd-figure'), figMedia:b('.bd-figure-media'), figTag:b('.bd-figure-tag')," +
  "plate:b('.bd-plate'), pool:b('.bd-pool')," +
  "logs:b('.bd-logs'), actions:b('.bd-actions')," +
  "styleField:(function(){var e=document.querySelector('.bd-field');if(!e)return '-';" +
  "var c=getComputedStyle(e);return {pt:c.paddingTop,pb:c.paddingBottom,minH:c.minHeight,mh:c.marginBottom};})()" +
  /* 战场那一行到底是谁撑起来的：把两个格子的直接子元素逐个量出来。
     实测 hero 内容只有 ~217 却占 292——多出来的 75px 必须找到出处。 */
  ",rows:(function(){var e=document.querySelector('.bd-field');if(!e)return '-';" +
  "return getComputedStyle(e).gridTemplateRows;})()," +
  "heroKids:(function(){var e=document.querySelector('.bd-hero');if(!e)return [];" +
  "var o=[];for(var i=0;i<e.children.length;i++){var k=e.children[i];" +
  "var r=k.getBoundingClientRect();var c=getComputedStyle(k);" +
  "o.push({cls:String(k.className).slice(0,26),top:Math.round(r.top),h:Math.round(r.height)," +
  "disp:c.display,mt:c.marginTop,mb:c.marginBottom,pt:c.paddingTop,pb:c.paddingBottom});}return o;})()," +
  "bossKids:(function(){var e=document.querySelector('.bd-boss');if(!e)return [];" +
  "var o=[];for(var i=0;i<e.children.length;i++){var k=e.children[i];" +
  "var r=k.getBoundingClientRect();var c=getComputedStyle(k);" +
  "o.push({cls:String(k.className).slice(0,26),top:Math.round(r.top),h:Math.round(r.height)," +
  "disp:c.display,mt:c.marginTop,mb:c.marginBottom,pt:c.paddingTop,pb:c.paddingBottom});}return o;})()" +
  "};})())";

/* 计算值：谁把战场那一行撑到 561 的 */
const STYLES = "JSON.stringify((function(){" +
  "function g(sel){var e=document.querySelector(sel);if(!e)return '-';" +
  "var c=getComputedStyle(e);var r=e.getBoundingClientRect();" +
  "return {h:Math.round(r.height),height:c.height,minH:c.minHeight,maxH:c.maxHeight," +
  "align:c.alignItems,justify:c.justifyContent,flex:c.flex,ar:c.aspectRatio,pb:c.paddingBottom,pt:c.paddingTop};}" +
  "return {field:g('.bd-field'), hero:g('.bd-hero'), fig:g('.bd-figure')," +
  "guide:g('.bd-field-guide'), media:g('.bd-figure-media')," +
  "plate:g('.bd-plate'), body:g('.bd-body'), portrait:g('.bd-hero-portrait')," +
  "progress:g('.bd-player-progress'), pool:g('.bd-pool')," +
  "wrapClass:(document.querySelector('.scene')||{}).className," +
  "arenaVar:(function(){var e=document.querySelector('.scene.boss-raid');" +
  "return e?getComputedStyle(e).getPropertyValue('--bd-arena').trim():'-';})()," +
  "vhPx:(function(){var d=document.createElement('div');d.style.cssText=" +
  "'position:fixed;left:-9px;top:0;height:100vh;width:1px';document.body.appendChild(d);" +
  "var h=d.getBoundingClientRect().height;document.body.removeChild(d);return Math.round(h);})()" +
  "};})())";

ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: W, height: H, deviceScaleFactor: 1, mobile: W < 700});

  const go = async (ms) => {
    /* 回选关榜要用 reload，不能用 navigate：
       **导航到同一个 URL 是空操作**（hash 没变，Chrome 直接忽略），
       页面不会重载，于是第 2 关起读到的还是第 1 关的战斗界面——
       症状是"21 关全是同一张图"，很像取用坏了，其实是没回退。 */
    await send('Page.reload', {ignoreCache: false});
    await wait(ms || 2600);
  };
  await send('Page.navigate', {url: process.argv[5]});
  await wait(4200);
  /* 全部解锁：unlocked(i) = i<=0 || isCleared(i-1)，所以 cleared 要有全部序号 */
  await ev("(function(){var all=[];for(var i=0;i<21;i++)all.push(i);" +
    "App.store.set('bossraid',{cleared:all,perfect:all});return 'seeded';})()");
  await go(2800);

  let n = await ev("document.querySelectorAll('.bo-board .bo-bead').length");
  n = Math.min(n, MAXLV || n);
  console.log('BEADS:' + n);

  const rows = [];
  for (let i = 0; i < n; i++) {
    /* ① 选关榜：悬停前应是本档通用图，悬停后应换成这一关自己要打的那尊。
       两个都读，否则"悬停没换图"与"本来就是这张"分不清。 */
    const trBefore = await ev(TRACK(i));
    await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + i +
      "];if(!b)return 'none';" +
      "b.dispatchEvent(new PointerEvent('pointerenter',{bubbles:false}));return 'ok';})()");
    await wait(420);
    const tr = await ev(TRACK(i));
    await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + i +
      "];if(b)b.dispatchEvent(new PointerEvent('pointerleave',{bubbles:false}));return 'ok';})()");
    /* ② 进关，读战斗台里的怪像 */
    await ev("(function(){var b=document.querySelectorAll('.bo-board .bo-bead')[" + i +
      "];if(b&&!b.disabled)b.click();return !!b;})()");
    await wait(1500);
    const fg = await ev(FIGHT);
    if (i === 0) {
      console.log('BOXES:' + await ev(BOXES));
      console.log('STYLES:' + await ev(STYLES));
    }
    const title = await ev("(function(){var h=document.querySelector('.bd-side-name b');" +
      "if(h)return h.textContent;var s=document.querySelector('.bd-side-role');" +
      "return s?s.textContent:'-';})()");
    rows.push({i: i, trackBefore: trBefore, track: tr, fight: fg, name: title});
    console.log('LV' + i + ':' + JSON.stringify({before: trBefore, track: tr, fight: fg, label: title}));
    /* 回选关榜：换关只有重进这一条路（进关后路由不变） */
    if (i + 1 < n) { await go(2400); }
  }
  console.log('ROWS:' + JSON.stringify(rows));
  console.log('ERRS:' + JSON.stringify(ERRS.slice(0, 12)));
  await send('Browser.close').catch(() => {});
});
'''

PORT = 9333
PROF = os.path.join(REPO, "_check", "bossartprof-%d" % int(time.time()))


def free_port(p):
    import socket
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p))
        return True
    finally:
        s.close()


def main():
    port = PORT
    while not free_port(port):
        port += 1
    js = os.path.join(REPO, "_check", "_bossart_cdp.cjs")
    os.makedirs(os.path.dirname(js), exist_ok=True)
    with open(js, "w", encoding="utf-8") as f:
        f.write(CDP)

    proc = subprocess.Popen([
        EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
        "--disable-extensions", "--remote-debugging-port=%d" % port,
        "--user-data-dir=%s" % PROF, "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ws_url = None
    for _ in range(80):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=1) as r:
                tabs = json.loads(r.read().decode("utf-8"))
            for t in tabs:
                if t.get("type") == "page":
                    ws_url = t["webSocketDebuggerUrl"]
                    break
            if ws_url:
                break
        except Exception:
            pass
        time.sleep(0.25)

    if not ws_url:
        print("无法连上调试端口")
        proc.terminate()
        return 1

    p = subprocess.run([NODE, js, ws_url, str(W), str(H), URL, OUT, "0", "0", "0",
                        os.environ.get("ARTCHECK_MAX", "0")],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode("utf-8", "replace")
    print(out)
    try:
        proc.terminate()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
