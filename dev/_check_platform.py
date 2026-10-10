# -*- coding: utf-8 -*-
"""用 headless Edge 打开新平台，抓取控制台错误与 DOM 状态。
   结果写入 _check/report.txt，避免控制台编码问题。"""
import io, os, re, subprocess, sys, json

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
os.makedirs(os.path.join(NEW, "_check"), exist_ok=True)

PROBE = """
<pre id="__report" style="display:none"></pre>
<script>
(function(){
  var logs = [];
  window.addEventListener('error', function(e){
    logs.push('ERROR: ' + (e.message || '') + ' @ ' + (e.filename || '') + ':' + (e.lineno || ''));
  });
  window.addEventListener('unhandledrejection', function(e){
    logs.push('REJECT: ' + (e.reason && e.reason.message ? e.reason.message : e.reason));
  });
  var ow = console.error;
  console.error = function(){ logs.push('CONSOLE.ERROR: ' + Array.prototype.join.call(arguments, ' ')); ow.apply(console, arguments); };
  window.addEventListener('load', function(){
    setTimeout(function(){
      var L = [];
      L.push('=== 控制台 ===');
      L.push(logs.length ? logs.join('\\n') : '(无错误)');
      L.push('');
      L.push('=== 平台状态 ===');
      var Z = window.__ZQ__;
      L.push('__ZQ__ 存在: ' + !!Z);
      if (Z) {
        L.push('版本: ' + Z.version);
        L.push('已注册模式数: ' + Z.modes.count());
        Z.modes.all().forEach(function(m){
          L.push('   - ' + m.id + '  ' + m.name + '  状态=' + m.status);
        });
        L.push('内容包类型: ' + Z.packs.types().join(','));
        Z.packs.types().forEach(function(t){
          L.push('   - ' + t + ' : ' + Z.packs.byType(t).length + ' 个');
        });
        L.push('当前路由: ' + JSON.stringify(Z.router.current()));
      }
      L.push('');
      L.push('=== DOM ===');
      L.push('站点标题文本: ' + (document.querySelector('.brand') || {}).textContent);
      L.push('品牌字形 src 长度: ' + ((document.querySelector('.brand-glyph') || {}).src || '').length);
      L.push('场景子节点数: ' + (document.getElementById('sceneRoot') || {}).children.length);
      L.push('首页卡片数: ' + document.querySelectorAll('.home-card').length);
      L.push('');
      L.push('=== 主题 ===');
      L.push('data-theme: ' + document.documentElement.getAttribute('data-theme'));
      L.push('body 背景图: ' + (getComputedStyle(document.body).backgroundImage || '').slice(0, 60));
      L.push('--ink 计算值: ' + getComputedStyle(document.documentElement).getPropertyValue('--ink').trim());
      L.push('--bone 计算值: ' + getComputedStyle(document.documentElement).getPropertyValue('--bone').trim());
      document.getElementById('__report').textContent = L.join('\\n');
    }, 500);
  });
})();
</script>
"""

src = io.open(os.path.join(NEW, "index.html"), encoding="utf-8").read()
tmp = src.replace("</body>", PROBE + "\n</body>", 1)
tmp_path = os.path.join(NEW, "_check", "probe.html")
io.open(tmp_path, "w", encoding="utf-8").write(tmp)

ud = os.path.join(NEW, "_check", "edgeprofile")
os.makedirs(ud, exist_ok=True)
url = "file:///" + tmp_path.replace("\\", "/")
cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
       "--force-device-scale-factor=1", "--window-size=520,1600",
       "--user-data-dir=" + ud, "--virtual-time-budget=6000",
       "--dump-dom", url]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=180)
dom = r.stdout or ""
m = re.search(r'<pre id="__report"[^>]*>(.*?)</pre>', dom, re.S)
rep = m.group(1) if m else "(未取到报告)"
rep = (rep.replace("&lt;", "<").replace("&gt;", ">")
          .replace("&amp;", "&").replace("&quot;", '"'))
io.open(os.path.join(NEW, "_check", "report.txt"), "w", encoding="utf-8").write(rep)
print("已写出 _check/report.txt | dom 长度", len(dom), "| exit", r.returncode)
if r.returncode != 0:
    print("stderr:", (r.stderr or "")[:400])
