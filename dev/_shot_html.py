# -*- coding: utf-8 -*-
"""给一份本地 HTML 出一张整页长图（用来核对交付说明页真的排对了）。

用法：python dev/_shot_html.py <html路径> <宽> <输出png>
例：  python dev/_shot_html.py 交付说明-第三关形象与竖排.html 1160 out/_deliverable_shot.png
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

SRC = sys.argv[1]
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1160
OUT = sys.argv[3] if len(sys.argv) > 3 else "_check/_htmlshot.png"
if not os.path.isabs(OUT):
    OUT = os.path.join(REPO, OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

if not SRC.startswith("file:"):
    SRC = "file:///" + os.path.abspath(os.path.join(REPO, SRC)).replace("\\", "/")

CDP = r'''
const fs = require('fs');
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
ws.addEventListener('message', e => { const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const call = async (m, p) => {
  const r = await send(m, p);
  if (r && r.error) { throw new Error(m + ' -> ' + JSON.stringify(r.error)); }
  return r && r.result;
};
const ev = async (x) => { const a = await call('Runtime.evaluate',
  {expression: x, returnByValue: true}); return a && a.result && a.result.value; };
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const OUT = process.argv[5];
const die = (e) => { console.log('ERR:' + (e && e.message ? e.message : e));
  ws.close(); process.exit(0); };
ws.addEventListener('open', async () => {
  try {
    await call('Page.enable');
    await call('Emulation.setDeviceMetricsOverride',
      {width: +process.argv[3], height: 900, deviceScaleFactor: 1, mobile: false});
    console.log('NAV:' + process.argv[4]);
    await call('Page.navigate', {url: process.argv[4]});
    await wait(2200);
    const info = await ev('JSON.stringify({h:document.documentElement.scrollHeight,' +
      'tables:document.querySelectorAll("table").length,' +
      'imgs:document.querySelectorAll("img").length,' +
      'broken:(function(){var o=[],a=document.images;for(var i=0;i<a.length;i++)' +
      'if(!a[i].complete||!a[i].naturalWidth)o.push(a[i].getAttribute("src"));return o;})()})');
    console.log('INFO:' + info);
    const m = await call('Page.getLayoutMetrics');
    const size = (m && (m.cssContentSize || m.contentSize)) || {width: +process.argv[3], height: 900};
    console.log('SIZE:' + JSON.stringify(size));
    const shot = await call('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: true,
      clip: {x: 0, y: 0, width: Math.ceil(size.width),
             height: Math.min(Math.ceil(size.height), 16000), scale: 1},
    });
    if (!shot || !shot.data) { return die('captureScreenshot 无数据'); }
    fs.writeFileSync(OUT, Buffer.from(shot.data, 'base64'));
    console.log('SHOT:' + OUT);
    ws.close();
  } catch (e) { die(e); }
});
ws.addEventListener('error', (e) => console.log('WSERR:' + (e && e.message ? e.message : e)));
'''

PORT = 9388
PROF = os.path.join(REPO, "_check", "htmlprof-%d" % int(time.time()))


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
    js = os.path.join(REPO, "_check", "_htmlshot_cdp.cjs")
    os.makedirs(os.path.dirname(js), exist_ok=True)
    with open(js, "w", encoding="utf-8") as f:
        f.write(CDP)
    proc = subprocess.Popen([
        EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
        "--disable-extensions", "--remote-debugging-port=%d" % port,
        "--user-data-dir=%s" % PROF, "--allow-file-access-from-files", "about:blank"],
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
    p = subprocess.run([NODE, js, ws_url, str(W), SRC, OUT],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(p.stdout.decode("utf-8", "replace"))
    try:
        proc.terminate()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
