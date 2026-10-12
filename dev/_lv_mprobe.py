# -*- coding: utf-8 -*-
"""量手机端每块展板内部：是字形栏高、还是文字栏高在撑卡片。

三块高度 165/187/264 参差不齐，得先知道差在哪，别瞎调 padding。
"""
import io, json, os, subprocess, sys, time, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")
W = int(sys.argv[1]) if len(sys.argv) > 1 else 390
H = int(sys.argv[2]) if len(sys.argv) > 2 else 844

PROBE = r"""(function(){
  function h(e){ return e ? Math.round(e.getBoundingClientRect().height) : -1; }
  var ps = [].slice.call(document.querySelectorAll('.lv'));
  return JSON.stringify(ps.map(function(p){
    var cs = getComputedStyle(p);
    var d = p.querySelector('.lv-desc');
    var lh = d ? parseFloat(getComputedStyle(d).lineHeight) : 0;
    var dh = h(d);
    return {
      name: (p.querySelector('.lv-name')||{}).textContent,
      card: Math.round(p.getBoundingClientRect().height),
      padT: cs.paddingTop, padB: cs.paddingBottom, dir: cs.flexDirection,
      art: h(p.querySelector('.lv-art')),
      body: h(p.querySelector('.lv-body')),
      name_h: h(p.querySelector('.lv-name')),
      tag_h: h(p.querySelector('.lv-tag')),
      desc_h: dh, desc_lines: lh ? Math.round(dh / lh) : 0,
      cut: d ? (d.scrollHeight - d.clientHeight) : 0,
      foot: (function(){var f=p.querySelector('.lv-foot');if(!f)return 'none';
        var r=f.getBoundingClientRect();return Math.round(r.height)+'@'+Math.round(r.top);})()
    };
  }));
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
  await new Promise(r => setTimeout(r, 4500));
  const a = await send('Runtime.evaluate', {expression: process.argv[6], returnByValue: true});
  console.log('R:' + ((a.result && a.result.value) || ''));
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_lvm.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9599
prof = os.path.join(OUT, "lvmprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), url, PROBE],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
o = None
for line in (r.stdout or "").splitlines():
    if line.startswith("R:"):
        o = json.loads(line[2:])
if not o:
    print((r.stdout or "")[:400]); print((r.stderr or "")[:300]); sys.exit(1)

print("  视口 %dx%d" % (W, H))
for p in o:
    print("  %s" % p["name"])
    print("    卡片高 %s　padding %s/%s　方向 %s" % (p["card"], p["padT"], p["padB"], p["dir"]))
    print("    字形栏 %s　文字栏 %s（名 %s + 一句话 %s + 说明 %s＝%s 行）"
          % (p["art"], p["body"], p["name_h"], p["tag_h"], p["desc_h"], p["desc_lines"]))
    print("    脚(说明+进入) 高@top %s" % p["foot"])

child.kill()
try:
    os.remove(ns)
except OSError:
    pass
