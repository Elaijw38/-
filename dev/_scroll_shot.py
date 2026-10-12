# -*- coding: utf-8 -*-
"""滚动到指定位置再截图（CDP）。

首屏是全幅大图，占满一屏，普通截图看不到下面的分区。
用法：python dev/_scroll_shot.py <url> <宽> <高> <滚动到> <输出png> [再滚一次]
"""
import io, json, os, subprocess, sys, time, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")

URL = sys.argv[1] if len(sys.argv) > 1 else "file:///" + os.path.join(REPO, "index.html").replace("\\", "/")
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1440
H = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
Y = int(sys.argv[4]) if len(sys.argv) > 4 else 900
PNG = sys.argv[5] if len(sys.argv) > 5 else os.path.join(OUT, "ui", "scrolled.png")

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
    {width: +process.argv[3], height: +process.argv[4], deviceScaleFactor: 1, mobile: false});
  await send('Page.navigate', {url: process.argv[5]});
  await new Promise(r => setTimeout(r, 5000));
  await send('Runtime.evaluate', {expression: 'window.scrollTo(0,' + process.argv[6] + ')'});
  await new Promise(r => setTimeout(r, 1200));
  /* 顺便报一下分区位置，便于核对节奏 */
  const a = await send('Runtime.evaluate', {expression:
    "JSON.stringify([].slice.call(document.querySelectorAll('.home-sec')).map(function(s){" +
    "var r=s.getBoundingClientRect();var cs=getComputedStyle(s);" +
    "return {t:Math.round(r.top+window.scrollY),h:Math.round(r.height),bt:cs.borderTopWidth,pt:cs.paddingTop};}))",
    returnByValue: true});
  console.log('SEC:' + ((a.result && a.result.value) || ''));
  const s = await send('Page.captureScreenshot', {format: 'png'});
  require('fs').writeFileSync(process.argv[7], Buffer.from(s.data, 'base64'));
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_scroll.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9622
prof = os.path.join(OUT, "scrollprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"], str(W), str(H), URL, str(Y), PNG],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
for line in (r.stdout or "").splitlines():
    if line.startswith("SEC:"):
        secs = json.loads(line[4:])
        print("  分区（top / 高 / 上罫线 / 上内边距）：")
        for s in secs:
            print("    top=%-6s h=%-5s borderTop=%-5s paddingTop=%s"
                  % (s["t"], s["h"], s["bt"], s["pt"]))
if r.stderr:
    print("  stderr: " + r.stderr[:200])
print("  截图 %s  %d B" % (PNG, os.path.getsize(PNG) if os.path.exists(PNG) else 0))
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
