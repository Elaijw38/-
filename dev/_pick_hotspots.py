# -*- coding: utf-8 -*-
"""热点坐标拾取器：点图上的实物 → 直接记下 2624×1472 像素坐标。

为什么需要它：
  位置清单必须与实物严丝合缝，而我**不能可靠地用肉眼估坐标**
  （这个项目已经因为"目测坐标"踩过一次：HANDOFF 记着 Edge 最小视口 482px 那次假结论）。
  所以做成工具：你看图点实物，程序记录真实像素坐标。

用法：
  python dev/_pick_hotspots.py <地图文件> <字表，逗号分隔>
  例：python dev/_pick_hotspots.py out/level2-maps/level2-01-sky-天象.jpg "日,月,雨,火"

操作：
  · 会弹出一个 Edge 窗口，图按 1:1 显示（图很宽，用底部滚动条左右移动）
  · 依次点每个字对应的实物；点完一个自动跳到下一个
  · 点错了按 Z 撤销上一步；按 S 保存并退出；按 Q 不保存退出
  · 结果写到同名 .hotspots.json，格式：{ char, x, y } 列表
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

REPO = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NODE = r"C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
OUT = os.path.join(REPO, "_check")

PAGE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>热点坐标拾取</title>
<style>
  html,body{margin:0;background:#1b1713;color:#f0e4cf;font:14px/1.6 "Microsoft YaHei",sans-serif}
  #bar{position:fixed;top:0;left:0;right:0;height:52px;z-index:9;display:flex;
       align-items:center;gap:14px;padding:0 16px;background:#241d16;
       border-bottom:1px solid #55442f}
  #bar b{color:#ffd79a;font-size:17px}
  #bar .k{color:#9c8a70}
  #wrap{position:absolute;top:52px;left:0;right:0;bottom:26px;overflow:auto;background:#0f0c09}
  #stage{position:relative;width:2624px;height:1472px}
  #stage img{position:absolute;inset:0;width:2624px;height:1472px;display:block;
             image-rendering:auto;cursor:crosshair}
  .mk{position:absolute;transform:translate(-50%,-50%);pointer-events:none;
      width:34px;height:34px;border:2px solid #ff5a3c;border-radius:50%;
      box-shadow:0 0 0 2px rgba(0,0,0,.5)}
  .mk span{position:absolute;left:36px;top:-2px;white-space:nowrap;color:#ffd79a;
           font-size:22px;font-weight:700;text-shadow:0 0 4px #000,0 0 8px #000}
  #hint{position:fixed;bottom:0;left:0;right:0;height:26px;line-height:26px;
        padding-left:16px;background:#241d16;border-top:1px solid #55442f;color:#c9b79a}
</style></head>
<body>
<div id="bar">正在标：<b id="cur">—</b>
  <span id="prog"></span>
  <span style="margin-left:auto;color:#9c8a70">点实物 · Z 撤销 · S 保存退出 · Q 放弃</span>
</div>
<div id="wrap"><div id="stage"><img id="im" alt=""><div id="mks"></div></div></div>
<div id="hint">图按 1:1 显示，用底部滚动条左右移动</div>
<script>
var CHARS = __CHARS__;
var SRC = "__SRC__";
var marks = [];
var stage = document.getElementById('stage');
var mks = document.getElementById('mks');
document.getElementById('im').src = SRC;
function draw(){
  mks.innerHTML = '';
  marks.forEach(function(m){
    var d = document.createElement('div');
    d.className = 'mk';
    d.style.left = m.x + 'px'; d.style.top = m.y + 'px';
    d.innerHTML = '<span>' + m.char + '</span>';
    mks.appendChild(d);
  });
  var next = CHARS[marks.length];
  document.getElementById('cur').textContent = next || '（已点完）';
  document.getElementById('prog').textContent =
    '已完成 ' + marks.length + ' / ' + CHARS.length;
}
stage.addEventListener('click', function(e){
  if (marks.length >= CHARS.length) return;
  var r = stage.getBoundingClientRect();
  var x = Math.round(e.clientX - r.left);
  var y = Math.round(e.clientY - r.top);
  if (x < 0 || y < 0 || x > 2624 || y > 1472) return;
  marks.push({ char: CHARS[marks.length], x: x, y: y });
  draw();
});
window.addEventListener('keydown', function(e){
  var k = e.key.toLowerCase();
  if (k === 'z') { marks.pop(); draw(); }
  if (k === 's') { window.__PICK_DONE__ = JSON.stringify(marks); document.title = 'DONE'; }
  if (k === 'q') { window.__PICK_DONE__ = '[]'; document.title = 'DONE'; }
});
draw();
</script></body></html>
"""


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    img = sys.argv[1]
    chars = [c.strip() for c in sys.argv[2].replace("，", ",").split(",") if c.strip()]
    if not os.path.isabs(img):
        img = os.path.join(REPO, img)
    if not os.path.exists(img):
        print("  !! 找不到地图：%s" % img)
        return 1

    rel = os.path.relpath(img, REPO).replace("\\", "/")
    src = "http://127.0.0.1:8099/" + urllib.parse.quote(rel)
    html = PAGE.replace("__CHARS__", json.dumps(chars, ensure_ascii=False)) \
               .replace("__SRC__", src)
    page_path = os.path.join(REPO, "_pick.html")
    io.open(page_path, "w", encoding="utf-8").write(html)

    port = 9931
    prof = os.path.join(OUT, "pickprof")
    subprocess.run(["cmd", "/c", "rd", "/s", "/q", prof], capture_output=True)
    child = subprocess.Popen([EDGE, "--remote-debugging-port=%d" % port,
                              "--user-data-dir=" + prof,
                              "--window-size=1600,1000",
                              "--new-window",
                              "http://127.0.0.1:8099/_pick.html"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    targets = None
    for _ in range(80):
        time.sleep(0.4)
        try:
            targets = json.load(urllib.request.urlopen(
                "http://127.0.0.1:%d/json/list" % port, timeout=10))
            if any(t.get("type") == "page" and t.get("url", "").find("_pick.html") >= 0
                   for t in targets):
                break
        except Exception:
            pass
    page = [t for t in (targets or [])
            if t.get("type") == "page" and t.get("url", "").find("_pick.html") >= 0]
    if not page:
        print("  !! 没找到拾取页，请确认本地预览服务在 8099 端口运行")
        child.kill()
        return 1

    script = r'''
const ws = new WebSocket(process.argv[2]);
let id = 0; const pending = new Map();
const send = (m, p) => new Promise(r => { const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
ws.addEventListener('open', async () => {
  for (let i = 0; i < 1800; i++) {           /* 最多等 15 分钟 */
    await new Promise(r => setTimeout(r, 500));
    const r = await send('Runtime.evaluate', {expression:
      "JSON.stringify({done:!!window.__PICK_DONE__, v:window.__PICK_DONE__||null})",
      returnByValue: true});
    const s = r.result && r.result.value;
    if (!s) continue;
    const o = JSON.parse(s);
    if (o.done) { console.log('RESULT:' + o.v); process.exit(0); }
  }
  console.log('RESULT:[]'); process.exit(0);
});
'''
    ns = os.path.join(REPO, "_cdp_pick.js")
    io.open(ns, "w", encoding="utf-8").write(script)
    r = subprocess.run([NODE, ns, page[0]["webSocketDebuggerUrl"]],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1000)
    child.kill()

    res = None
    for line in (r.stdout or "").splitlines():
        if line.startswith("RESULT:"):
            res = json.loads(line[7:])
    if not res:
        print("  没有取得结果")
        return 1

    outp = os.path.splitext(img)[0] + ".hotspots.json"
    io.open(outp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(res, ensure_ascii=False, indent=1))
    print("  已记录 %d / %d 个热点 -> %s" % (len(res), len(chars), outp))
    for m in res:
        print("    %-4s x=%4d y=%4d" % (m["char"], m["x"], m["y"]))
    try:
        os.remove(ns)
        os.remove(page_path)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
