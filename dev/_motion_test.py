# -*- coding: utf-8 -*-
"""动效自检：滚动显现、字形描绘、底纹视差、控制台。

要验的是"真的发生了"，不是"代码写了"：
  · html.js-motion 有没有挂上（挂了才有隐藏态；没挂 = 内容照常可见）
  · 首屏元素应当**已经**是 rv-in（不该开局先闪一下）
  · 往下滚之后，下面的元素应当陆续变成 rv-in
  · 兜底：即使观察器不工作，2.5s 后视口内的也应显示
  · 字形描绘：mouseenter 之后应当产生进行中的动画
  · 底纹视差：pointermove 之后 --bg-x/--bg-y 应当变了
  · 控制台有无报错
"""
import io, json, os, subprocess, sys, time, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")
URL = sys.argv[1] if len(sys.argv) > 1 else "file:///" + os.path.join(REPO, "index.html").replace("\\", "/") + "#/modes"
PNG = os.path.join(OUT, "ui", "motion_before.png")

CDP = r'''
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map(); const errs = [];
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    errs.push((m.params.args || []).map(a => a.value || a.description || '').join(' '));
  }
  if (m.method === 'Runtime.exceptionThrown') {
    errs.push('EXC ' + JSON.stringify(m.params.exceptionDetails.exception || {}).slice(0, 120));
  }
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
const ev = (t, x, y) => send('Input.dispatchMouseEvent', {type: t, x, y, button: 'left', clickCount: 1});
const evalJs = async (expr) => {
  const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true});
  return r && r.result ? r.result.value : null;
};

ws.addEventListener('open', async () => {
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: process.argv[3]});
  await new Promise(r => setTimeout(r, 2600));

  console.log('A:' + await evalJs(`JSON.stringify({
    jsMotion: document.documentElement.classList.contains('js-motion'),
    rv: document.querySelectorAll('.mo-rv').length,
    rvIn: document.querySelectorAll('.mo-rv.mo-in').length,
    visible: (function(){
      var bad = 0, els = document.querySelectorAll('.mo-rv:not(.mo-in)');
      for (var i=0;i<els.length;i++){ var r=els[i].getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) bad++; }
      return bad;
    })(),
    scrollY: Math.round(window.scrollY)
  })`));

  // 滚到中间
  await evalJs('window.scrollTo(0, 900)');
  await new Promise(r => setTimeout(r, 1400));
  console.log('B:' + await evalJs(`JSON.stringify({
    rvIn: document.querySelectorAll('.mo-rv.mo-in').length,
    scrollY: Math.round(window.scrollY)
  })`));

  // 字形描绘：移到第 2 块展板上
  const pt = JSON.parse(await evalJs(`(function(){var p=document.querySelectorAll('.lv')[1];
    if(!p) return 'null'; var r=p.getBoundingClientRect();
    return JSON.stringify({x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2)});})()`));
  let drawn = null;
  if (pt) {
    await ev('mouseMoved', pt.x, pt.y);
    await new Promise(r => setTimeout(r, 260));
    drawn = await evalJs(`(function(){
      var g = document.querySelectorAll('.lv')[1].querySelector('.lv-glyph');
      if (!g || !g.getAnimations) return 'no-api';
      return g.getAnimations({subtree:true}).length;
    })()`);
  }
  console.log('C:' + JSON.stringify({drawn: drawn}));

  // 底纹视差
  const before = await evalJs("getComputedStyle(document.documentElement).getPropertyValue('--bg-x')");
  await ev('mouseMoved', 40, 40);
  await new Promise(r => setTimeout(r, 120));
  await ev('mouseMoved', 1380, 900);
  await new Promise(r => setTimeout(r, 700));
  const after = await evalJs("getComputedStyle(document.documentElement).getPropertyValue('--bg-x')");
  console.log('D:' + JSON.stringify({before: (before || '').trim(), after: (after || '').trim()}));

  const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(process.argv[4], Buffer.from(s.data, 'base64'));
  console.log('ERR:' + JSON.stringify(errs.slice(0, 5)));
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_motion.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9633
prof = os.path.join(OUT, "moprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], URL, PNG],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
out = {}
for line in (r.stdout or "").splitlines():
    for k in ("A", "B", "C", "D", "ERR"):
        if line.startswith(k + ":"):
            try:
                out[k] = json.loads(line[len(k) + 1:])
            except Exception:
                out[k] = line[len(k) + 1:]
if not out:
    print((r.stdout or "")[:500]); print((r.stderr or "")[:300]); sys.exit(1)

A, B = out.get("A", {}), out.get("B", {})
print("  ① 滚动显现")
print("     js-motion 已挂: %s（挂了才有隐藏态）" % A.get("jsMotion"))
print("     标记元素 .mo-rv: %s" % A.get("rv"))
print("     首屏已显示 .mo-in: %s　**视口内仍隐藏的: %s（应为 0）**" % (A.get("rvIn"), A.get("visible")))
print("     滚到 y=900 后 .mo-in: %s → %s" % (A.get("rvIn"), B.get("rvIn")))
print("  ② 字形描绘")
print("     hover 之后进行中的动画数: %s（>0 即真的在描）" % out.get("C", {}).get("drawn"))
print("  ③ 底纹视差")
D = out.get("D", {})
print("     --bg-x: %r → %r　%s" % (D.get("before"), D.get("after"),
      "变了 ✓" if D.get("before") != D.get("after") else "没变 X"))
print("  ④ 控制台错误: %s" % (out.get("ERR") or "无"))
print("  截图 %s" % PNG)

child.kill()
try:
    os.remove(ns)
except OSError:
    pass
