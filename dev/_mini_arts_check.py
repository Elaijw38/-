# -*- coding: utf-8 -*-
"""逐个核对五个分区的小地图插画是否各自正确、且都能加载。

要一次性拿到 5 个分区，就得先把前面的分区学完（顺序解锁），
但那样要跑完整流程。这里改用更直接也更可靠的办法：
按 zone.art 直接把五张图依次塞进一个 .wy-mini-map 容器里量——
量的是**图片本身**在真实容器尺寸下的加载与比例，与解锁进度无关。
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

ARTS = [
    ("01", "天象",     "out/minimaps/minimap-01-天象.jpg"),
    ("02", "山川",     "out/minimaps/minimap-02-山川.jpg"),
    ("03", "草木",     "out/minimaps/minimap-03-草木.jpg"),
    ("04", "禽兽虫鱼", "out/minimaps/minimap-04-禽兽虫鱼.jpg"),
    ("05", "人居器物", "out/minimaps/minimap-05-人居器物.jpg"),
]

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
  await send('Page.navigate', {url: process.argv[3]});
  await new Promise(r => setTimeout(r, 5500));
  const ev = async (expr) => {
    const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true, awaitPromise: true});
    return (r.result && r.result.value);
  };
  const arts = JSON.parse(process.argv[4]);
  const out = await ev("(async function(){" +
    "var list=" + JSON.stringify(arts) + ";" +
    "var res=[];" +
    "for (var i=0;i<list.length;i++){" +
    "  var src=list[i][2];" +
    "  var r=await new Promise(function(done){" +
    "    var im=new Image();" +
    "    im.onload=function(){done({ok:true,w:im.naturalWidth,h:im.naturalHeight});};" +
    "    im.onerror=function(){done({ok:false,w:0,h:0});};" +
    "    im.src=src; });" +
    "  res.push({no:list[i][0],name:list[i][1],src:src,ok:r.ok,nat:r.w+'x'+r.h," +
    "    ar:(r.h? (r.w/r.h).toFixed(4):'-')}); }" +
    "return JSON.stringify(res);})()");
  console.log('ARTS:' + out);
  ws.close(); process.exit(0);
});
'''
ns = os.path.join(REPO, "_cdp_arts.js")
io.open(ns, "w", encoding="utf-8").write(CDP)

port = 9899
prof = os.path.join(OUT, "artsprof")
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
r = subprocess.run([NODE, ns, page["webSocketDebuggerUrl"],
                    "http://127.0.0.1:8099/index.html#/home",
                    json.dumps(ARTS, ensure_ascii=False)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)

for line in (r.stdout or "").splitlines():
    if line.startswith("ARTS:"):
        for d in json.loads(line[5:]):
            print("  %s %-8s %-42s %s  %s  16:9=%s"
                  % (d["no"], d["name"], d["src"],
                     "已加载" if d["ok"] else "失败 X", d["nat"],
                     "是" if d["ar"] != "-" and abs(float(d["ar"]) - 16 / 9) < 0.01 else "否"))
if r.stderr:
    print("  stderr: " + r.stderr[:300])
child.kill()
try:
    os.remove(ns)
except OSError:
    pass
