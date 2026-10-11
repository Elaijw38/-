# -*- coding: utf-8 -*-
"""甲骨构字 · 手机端构件台量测。

为什么要 CDP：Edge 无头窗口有最小宽度（实测 482px），
--window-size=390 量到的是 482px 布局再裁切，会得出假结论。

做两件事：
  1 生成 _wrap_bb.html（进对局 + 把量测写进 data-bone），
    这个包装页也能直接喂给 dev/_mobile.js 出截图
  2 量对局页每一块的高度，判断"构件台能否一屏看完"

一屏看完的判定必须**扣掉底部固定操作栏**——
它是 position: fixed，会盖在内容上；只比"底边 ≤ 视口高"会假通过。

用法：python dev/_bb_audit.py [宽] [高]
"""
import io, json, os, subprocess, sys, time, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")

W = int(sys.argv[1]) if len(sys.argv) > 1 else 390
H = int(sys.argv[2]) if len(sys.argv) > 2 else 844

INJ = """
<script>
setTimeout(function () {
  var bs = document.querySelectorAll('button');
  for (var i = 0; i < bs.length; i++) {
    if (/^开始/.test((bs[i].textContent || '').trim())) { bs[i].click(); break; }
  }
  setTimeout(function () {
    function box(s){var e=document.querySelector(s);if(!e)return null;
      var r=e.getBoundingClientRect();
      return {t:Math.round(r.top+window.scrollY),h:Math.round(r.height),w:Math.round(r.width)};}
    var pcs = document.querySelectorAll('#mpPieces .piece');
    var tops = {}; for (var i=0;i<pcs.length;i++){ tops[Math.round(pcs[i].getBoundingClientRect().top)]=1; }
    var tray = box('#mpPieces');
    var fbar = document.querySelector('.stage > .info > .bar') || document.querySelector('.info > .bar');
    var barH = fbar ? Math.round(fbar.getBoundingClientRect().height) : 0;
    var usable = window.innerHeight - barH;
    document.documentElement.setAttribute('data-bone', JSON.stringify({
      vh: window.innerHeight, barH: barH, usable: usable,
      slots: box('#mpSlots'), tray: tray,
      pieces: pcs.length, rows: Object.keys(tops).length,
      trayInnerW: (function(){var e=document.querySelector('#mpPieces');return e?e.scrollWidth:0;})(),
      trayBottom: tray ? tray.t + tray.h : -1,
      fits: tray ? (tray.t + tray.h) <= usable : null
    }));
  }, 1800);
}, 1200);
</script>
"""

_src = io.open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
WRAP = os.path.join(REPO, "_wrap_bb.html")
io.open(WRAP, "w", encoding="utf-8").write(_src.replace("</body>", INJ + "\n</body>", 1))
url = "file:///" + WRAP.replace("\\", "/") + "#/play/bone-build"

PROBE = r"""(function(){
  function info(e){
    var r = e.getBoundingClientRect();
    var cls = (e.className && e.className.baseVal !== undefined) ? e.className.baseVal : (e.className || '');
    return {tag: e.tagName.toLowerCase(), cls: String(cls).slice(0,34),
            t: Math.round(r.top + window.scrollY), h: Math.round(r.height)};
  }
  var host = document.querySelector('.mode-host');
  var out = {vh: window.innerHeight, items: []};
  if (host) {
    var all = host.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var r = all[i].getBoundingClientRect();
      if (r.height >= 22 && r.width > 200) {
        var o = info(all[i]);
        o.depth = (function(n){var d=0;while(n&&n!==host){d++;n=n.parentElement;}return d;})(all[i]);
        out.items.push(o);
      }
    }
  }
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
ws.addEventListener('open', async () => {
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1, mobile: true});
  await send('Page.navigate', {url: process.argv[5]});
  await new Promise(r => setTimeout(r, 5500));
  const a = await send('Runtime.evaluate', {expression: process.argv[6], returnByValue: true});
  console.log('R:' + ((a.result && a.result.value) || ''));
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_bb.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9577
prof = os.path.join(OUT, "bbmprof")
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

r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), url, PROBE],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
o = None
for line in (r.stdout or "").splitlines():
    if line.startswith("R:"):
        o = json.loads(line[2:])
if not o:
    print((r.stdout or "")[:400])
    print((r.stderr or "")[:300])
    sys.exit(1)

print("  视口 %dx%d　高 %s" % (W, H, o["vh"]))
print("  对局区里高度 >=22 的元素（按 top 排序）：")
seen = set()
for it in sorted(o["items"], key=lambda x: (x["t"], -x["h"])):
    key = (it["cls"], it["t"])
    if key in seen:
        continue
    seen.add(key)
    print("    top=%-5s h=%-5s depth=%-3s %s.%s"
          % (it["t"], it["h"], it["depth"], it["tag"], it["cls"]))

child.kill()
try:
    os.remove(ns)
except OSError:
    pass
print("\n  包装页已生成：%s" % WRAP)
print('  截图：node dev/_mobile.js "file:///%s#/play/bone-build" %d %d out.png'
      % (WRAP.replace("\\", "/"), W, H))
