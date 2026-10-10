# -*- coding: utf-8 -*-
"""专项检查全局设置页：内容包区是否渲染、主题下拉是否正确、行数统计。
   直接以 #/settings 打开，并打印场景结构。"""
import io, os, re, subprocess

NEW = r"C:\DSH\字趣"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(NEW, "_check")
os.makedirs(OUT, exist_ok=True)

src = io.open(os.path.join(NEW, "index.html"), encoding="utf-8").read()
# 在 build.js 之后插入一段立即执行的检查（此时平台已启动）
CHECK = """
<script>
(function () {
  var L = [];
  function qa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  try {
    location.hash = '#/settings';
    App.router.render();
    L.push('路由: ' + JSON.stringify(App.router.current()));
    L.push('场景 .sect 数: ' + qa('.scene .sect').length);
    qa('.scene .sect').forEach(function (s, i) {
      var h = s.querySelector('h4');
      L.push('  [' + i + '] ' + (h ? h.textContent.trim() : '(无标题)') +
             '　子节点=' + s.children.length +
             '　表格行=' + s.querySelectorAll('table tr').length);
    });
    L.push('主题下拉选项: ' + qa('.scene select option').map(function (o) { return o.textContent; }).join(' / '));
    L.push('内容包表格是否存在: ' + (qa('.scene table').length));
    L.push('页面上的表格行总数: ' + qa('.scene table tr').length);
  } catch (e) {
    L.push('!! 异常: ' + (e && e.message ? e.message : e));
  }
  document.documentElement.setAttribute('data-report', L.join('\\n'));
})();
</script>
"""
tmp = src.replace('<script src="js/core/build.js"></script>',
                  '<script src="js/core/build.js"></script>' + CHECK, 1)
p = os.path.join(NEW, "_shot_settings.html")
io.open(p, "w", encoding="utf-8").write(tmp)
url = "file:///" + p.replace("\\", "/")
r = subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + os.path.join(OUT, "edgeprofile"),
                    "--virtual-time-budget=8000", "--dump-dom", url],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=180)
c = r.stdout or ""
io.open(os.path.join(OUT, "set_dom.html"), "w", encoding="utf-8").write(c)
m = re.search(r'data-report="(.*?)"', c, re.S)
rep = m.group(1) if m else "(未取到)"
rep = (rep.replace("&quot;", '"').replace("&#39;", "'").replace("&#10;", "\n")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
print(rep)
try:
    os.remove(p)
except OSError:
    pass
