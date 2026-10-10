# -*- coding: utf-8 -*-
"""把真实甲骨文字形纹样注入 index.html，作为页面底纹。
   在 build.js 之前插入一段内联脚本，把 URI 赋给 App.OB_PATTERN。
   来源：hanzi-glyphs-svg（CC BY 4.0），见页脚署名。"""
import io, os
from urllib.parse import quote

NEW = r"C:\DSH\字趣"
SVG = r"C:\DSH\四创大赛_字从契来\_bg_oracle.svg"
if not os.path.exists(SVG):
    raise SystemExit("缺少纹样文件：" + SVG)

svg = io.open(SVG, encoding="utf-8").read()
# 深色主题下纹样要用浅色描边才看得见；这里把填色换成跟着主题走的变量不可行（SVG 在 data URI 里），
# 因此给出一个中性的暖褐，配合 theme.css 的混合模式使用。
uri = "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")

P = os.path.join(NEW, "index.html")
s = io.open(P, encoding="utf-8").read()

BLOCK = ('<!-- 页面底纹：真实甲骨文字形（运行期注入，见 build.js 的 injectPattern） -->\n'
         '<script>window.App = window.App || {}; App.OB_PATTERN = "%s";</script>\n' % uri)

if 'App.OB_PATTERN = "' not in s:
    s = s.replace('<script src="js/core/data.js"></script>', BLOCK + '<script src="js/core/data.js"></script>', 1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("OK 已注入纹样（%.1f KB）" % (len(uri) / 1024))
else:
    # 已存在则替换内容
    import re
    s = re.sub(r'App\.OB_PATTERN = "[^"]*";', 'App.OB_PATTERN = "' + uri + '";', s, count=1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("OK 已更新纹样（%.1f KB）" % (len(uri) / 1024))

print("index.html 现在 %.0f KB" % (len(io.open(P, encoding='utf-8').read()) / 1024))
