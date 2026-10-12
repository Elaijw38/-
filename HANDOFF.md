# 接入说明 · 字趣 · 甲骨构字记

> 给接手的 AI 会话看。读完这一份就能继续，不必回翻历史。
> 最后更新：本次会话结束时。

---

## 0. 先做三件事

```powershell
# 1 确认仓库状态（下面「二」有当前预期值）
cd C:\DSH\字趣
git log --oneline -3
git status --porcelain

# 2 确认代码可用
& 'C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe' dev\_syntax_probe.js
& 'C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe' dev\_verify_deploy.js .

# 3 起本地预览（改了要给人看，站点的所有路径都是相对的，file:// 也能开）
#    端口占用就往上找
python -m http.server 8099
```

**环境路径**（本机固定，不要另找解释器）：
- Python：`C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
- Node：`C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`
- Edge：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
- LibreOffice kit：见 `office-pptx` skill 的 Installed LibreOffice Kit 段

---

## 1. 项目是什么

面向**甲骨文**的汉字文化互动平台（教育、非商业）。用甲骨字形本身做玩法。

| | |
|---|---|
| 仓库 | `C:\DSH\字趣` |
| 远端 | `github.com/Elaijw38/jiagugouciji` |
| 线上 | https://elaijw38.github.io/jiagugouciji/ |
| 技术栈 | **纯 `<script>` + 全局 `App` 命名空间；无框架、无构建、无依赖、双击即开** |
| 规模 | 产品代码 **8105 行 / 19 个文件**（index.html + css×4 + js）—— 实测口径 |
| 部署 | GitHub Pages；`deploy.ps1` 会 commit + push（**未经用户明确说"推"不要跑**） |

**路由**：`#/home` `#/modes` `#/atlas` `#/howto` `#/settings` `#/play/:modeId`

**三个玩法**（设定不可擅改）：

| id | 名称 | 一句话 | 备注 |
|---|---|---|---|
| `bone-build` | 甲骨构字 | 龟宝带玩家认识甲骨文，再完成构件入门练习 | **第一关**，单人、无倒计时，5 次练习；每题伴随甲骨知识与答后讲解 |
| `wangyi-map` | 殷商王邑 | 学习主题小地图，点亮对应王邑区域并解锁下一幅 | **主玩法**，5 幅主题框架；61 个现有字形学习点，主题待用户提供 |
| `boss-raid` | 构件讨伐 | 拆字为武、组构为招 | 21 关线性，横版对战 |

**数据规模**：73 个甲骨字形 · 37 构件 · 34 字卡 · 61 王邑实物 · 21 讨伐关 → 图鉴 **102 字 / 153 条目**

---

## 2. 仓库当前状态（接手时核对）

```
本地 HEAD  e251921   加强艺术感、互动性与主线：真字形底纹、纸面物质感、滚动显现、贯穿主线
远端        e42d35b   展板手机端：「进入」对不齐右边 + 出处被藏
```

**本地领先远端 1 个提交，未推送。**

**上一次那版「绿金皮」已被撤回。** 撤回前把它存成了 git tag，随时可查：

```powershell
git show wip-jade-gold-rejected --stat        # 那版改了什么
git show wip-jade-gold-rejected:css/theme.css | head -80
```

> 撤回的只是**外衣**（玉绿 + 鎏金那组令牌与用法，在 `css/theme.css` 与
> `js/core/build.js` 的字形配色里）。`js/core/shell.js` 里的 `sheetWrap()`
> **保留了**——"内容装在一块浅色面上"这个结构是对的，只是那个面已经从
> 羊皮纸卷轴改成了**骨版**（见「六」）。

**这次新增/改动的文件**：

| 文件 | 里面是什么 |
|---|---|
| `assets/bone.png` | **新增**。骨材质（斑驳 + 骨纹 + 虫蛀孔），512 无缝平铺，`dev/_gen_bone.py` 生成 |
| `css/theme.css` | 骨材质令牌、页底三层背景、`--edge` 压深、**兆纹**分区线令牌 |
| `css/ui.css` | `.sheet` 骨版、图鉴改**拓片集**、`.home-sec` 叠兆纹 |
| `css/modes.css` | `.ac-glyph path` 线宽 1.9 → 2.4px（反白字发虚，必须加粗） |
| `js/core/build.js` | 刻辞底纹加深（真看得见）、撤掉多余的那层 SVG 网格 |
| `js/core/shell.js` | 保留 `sheetWrap()`；拓片卡新增 `.ac-rub`（朱笔今字） |

---

## 3. 用户明确的约束（违反即返工）

1. **不推送远程**，除非用户明确说「推」。其余时间最多提交到本地。
2. **不覆盖用户未提交的修改**。动手前先 `git status`。
3. **只按用户明确授权改玩法** —— 当前用户已明确授权第一关改为龟宝引导的单人入门课，边拼字边学甲骨知识；第二关改为主题小地图逐幅解锁，完成一幅点亮王邑总图对应区域。五个主题先沿用现有数据分区作可替换占位，收到用户主题后再替换名称与教学内容；字形数据与历史事实不编造，第三关 Boss 流程保留。这个决定覆盖此前对第一、二关“玩法流程不动”的旧要求。
4. **绝不编造甲骨字形。** 字形一律取自 `App.glyphs.parts`（73 个）；合体字数据集里没有整字甲骨形（这是真实情况），退用构件并排组合，并**标明「组合示意」**。
5. **甲骨形上不直接印现代字** —— 默认隐藏，悬停 / `:focus-visible` / `:active` 才显现。（这条用户强调过两次，我曾"为了可用性"妥协成半透明，被纠正。）
6. **署名必须保留**：字形数据 CC BY 4.0（Qing-sheng Li & Yu-lin Bian；镜像 `github.com/zhouyongh/hanzi-glyphs-svg`）/ 首页骨片照 CC0（Gary Todd）/ 当前王邑总图为项目原创学习示意（非考古复原），仓库保留的旧版底图由 Agnes AI 生成。页面与 README 均须准确区分新旧地图来源。
7. 用户**极其简短**，讨厌反问，要看到"真的改了 + 真的测了"。汇报要**诚实**：不确定的说不确定，自己犯的错要讲。

---

## 4. 技术陷阱（都踩过，勿重蹈）

| 坑 | 症状 | 正解 |
|---|---|---|
| **Edge 无头最小视口 482px** | 用 `--window-size=390` 量手机，得到的是 482px 布局再裁切，得出"移动端横向溢出"的**假结论** | 必须走 CDP `Emulation.setDeviceMetricsOverride`（见 `dev/_mobile.js`） |
| **状态类撞名** | 我给滚动显现加 `.rv`，而 `.rv` 是玩法"复盘"块的旧类名（带 `background: var(--bone-hi)`），导致每个标记元素被涂成白底 | 加状态类前先 grep 一遍。现用 `.mo-rv / .mo-in` |
| **`getBoundingClientRect` 含 transform** | 显现动画平移 16px，使"三块底边对齐"检查误判为否 | 测**布局**用 `offsetTop/offsetHeight` |
| **显隐动效没兜底** | 观察器不工作时内容永久不可见 | 隐藏态只在 `html.js-motion` 下生效（JS 自己挂）+ 2.5s 强制显示 |
| **CSS 内联 `feTurbulence` SVG 当背景** | 单独渲染正常，但作为 CSS 背景 `backgroundImage` 恒为 `none`（各种编码都试过） | 用 PNG（`assets/bone.png`）。简单的 `path` + `stroke-opacity` 那种 data URI 是好的（`--crack` 就是） |
| **`100vw` 含滚动条宽** | 页面可横向挪动 10px；改用 `overflow-x: hidden` 又**弄坏 sticky 顶栏** | 用 `overflow-x: clip`（不创建滚动容器） |
| **子类选择器权重** | `app.css` 的 `.stage > .info > .bar .btn.sm` 压过 `.info > .bar .btn.sm` | 用同等权重覆盖 |
| **筛选片数字口径** | 图鉴写"全部 102"（去重字数）点进去 153 条 | 牌子用**条目数**；去重字数留在页头 |
| **`--syntax` 内联 Python 被 PowerShell 吃引号** | `SyntaxError: unterminated string literal` | 补丁写成**文件**再跑，别用 `python -c "..."` |
| **PowerShell 管道截断会掐死上游进程** | `Select-Object -First N` 使 node 提前退出，截图没写完；**表现是 `[exit code: 1]`**，看着像测试挂了 | 别截断要跑完的进程。看到 exit 1 先单独重跑确认，别急着当成失败 |
| **`html[data-theme="bone"]` 权重高于 `:root`** | 只在 `:root` 改了 `--edge`，页面上**毫无变化** | 同一个令牌要在**两处**都改（`theme.css` 的 `:root` 与 `html[data-theme="bone"]`） |
| **SVG 的 `stroke-width` 写在 `<svg>` 上没用** | 字形结构是 `<svg><g><path stroke-width=".15"/></g></svg>`，那个是 path 的**表现属性**；外层写 CSS 不起作用（实测 CSS 2.8px → 实际 1.9px） | 线宽一律写 **path**，且口径在 `modes.css` 那一组 `non-scaling-stroke` 里（`ui.css` 后加载不了，同权重下 `modes.css` 胜） |
| **`opacity` 加在区块上** | 想让装饰背景淡一点，结果**整块内容**（含所有文字）一起变淡 | 装饰层的透明度写进它自己的 SVG/色值里，别用父级 `opacity` |
| **反复 `Runtime.evaluate` 轮询会让页面不长高** | 在 CDP 里循环量 `scrollHeight` 等"稳定"，页面反而恒停在 394px、`#sceneRoot` 为空；加 `Runtime.enable`/`Log.enable` 也一样 | 导航后**老实等一个固定时长**（5~6s）再量。`dev/_route_shot.py` 是好的，`dev/_probe_point.py` 是坏的 |

---

## 5. 验证套件（`dev/`，现 51 个工具）

改完**必须**跑，全绿才算完。

```powershell
$py  = 'C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$node= 'C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
cd C:\DSH\字趣

& $node dev\_syntax_probe.js          # 语法 + 缺失引用
& $node dev\_verify_deploy.js .       # index.html 每个引用能否精确命中（现 18 个）
& $node dev\_contrast.js              # 对比度；基线 = 1（只剩"描边/分隔线"非文字那对）
& $py   dev\_final_check.py           # 八个页面
& $py   dev\_run_shell.py             # 壳层（顶栏/路由/首页/图鉴/说明/展板/成就/页脚）
& $py   dev\_run_drive.py             # 甲骨构字
& $py   dev\_run_wy.py                # 殷商王邑（逐笔拖入 11/11）
& $py   dev\_run_bo.py                # 构件讨伐
& $node dev\_mobile.js <url> 390 844 out.png   # 手机端（CDP 真视口）★ 是 .js，要用 $node 跑
& $py   dev\_lv_test.py 1440 1000     # 展板悬停/点击（CDP 真鼠标）
& $py   dev\_motion_test.py <url>     # 滚动显现/字形描绘/视差
& $py   dev\_bb_audit.py 390 844      # 甲骨构字"一屏放得下"
& $py   dev\_scroll_shot.py <url> 1440 1000 760 out.png   # 滚动后截图
```

**本次新加的四个工具**：

```powershell
& $py dev\_gen_bone.py                          # 生成 assets/bone.png（骨材质），带接缝自检
& $py dev\_route_shot.py <route> <宽> <高> <png> [滚动到]
      # 按路由截图 + 报一把关键量：骨材质层是否生效、blend、横向溢出、
      # 刻辞底纹字符数、.sheet 数、.atlas-card 数、拓片字形的线宽/颜色
& $py dev\_scroll_diag.py <route> <宽> <高>      # 谁在滚、能不能滚（html/body/.wrap/… 全列）
& $py dev\_probe_point.py <route> <宽> <高> <x> <y> [滚动到]
      # 点探：某一点上的命中栈与盒模型 ★ 目前**不可靠**（页面常停在 394px），
      # 急着查某点归谁管时再修它，日常用 _route_shot.py
```

**四个 CSS 的花括号要配平**（`theme/ui/app/modes`）。**改动前记得 `git status`。**

---

## 6. 设计方向：卡在哪里，往哪走

### 用户的最终判断（原话）

> 「你做的好素 啊 而且空白好多 我不是跟你讲了 大胆去改」
> （给我看参考 PPT 之后）「**我们是甲骨文你就只会抄吗**」

### 我犯的两个错

**错一：做成了一张平的米色纸。**
原来是"骨白极简"——低饱和、无阴影、圆角归零、装饰全退。
结果**素、空白多**。骨白是对的，但我把"骨"理解成了"白色"。

**错二：照抄参考稿。**
用户给了 `走进甲骨看殷商.pptx`（8 页满版图，已提取到 `C:\DSH\_ppt_pics\v01..v08.jpg`），
那套是**深玉绿 + 鎏金 + 祥云 + 卷轴**。我照着做了 ✗
——但**祥云是明清纹样、玉绿鎏金是清代宫廷色，跟甲骨无关**。
套上去只能说明我会抄。

### 正解（已实施）

> **先把这一节读完再动手。** 上一版（骨材质 + 拓片铺满）虽然做了"材质"，
> 但方向仍然是错的——因为**我从没读过下面这三份实测规范**，
> 全靠自己想"该加点什么"。结果是把页面越糊越厚，用户直接说
> 「改的有什么意义 每次都这样 你能不能好好学习下优秀案例」。

#### 三家美术馆的实测规范（**必须真读，别猜**）

- [大阪中之島美術館 DESIGN.md](https://kzhrknt.github.io/awesome-design-md-jp/design-md/nakanoshima-museum/DESIGN.md)
- [森美術館 preview](https://kzhrknt.github.io/awesome-design-md-jp/design-md/mori-art-museum/preview.html)
  ／ [DESIGN.md](https://kzhrknt.github.io/awesome-design-md-jp/design-md/mori-art-museum/DESIGN.md)
- [東京都現代美術館 MOT DESIGN.md](https://kzhrknt.github.io/awesome-design-md-jp/design-md/mot-art-museum/DESIGN.md)
- 文化机构首页的实测结论：[文化机构官网首页排了十一件展品，安静的调性一下散了](https://www.jizankeji.com/zhishi/551.html)

**三家的共同点（这才是"优秀案例"的干货）**：

| 项目 | 中之岛 | 森 | MOT |
|---|---|---|---|
| 地色 | 纯白 `#ffffff` | 白 | 白 |
| 有彩色 | **0 个** | 1 个（绯红 `#bf0d3e`） | 1 个（链接蓝 `#356eb0`） |
| `box-shadow` | **声明 0 件** | 不用，靠面色 | 几乎全 `none` |
| 层次 | 1px `#808080` 罫 | 面色浓淡 | `#ffffff/#f1f1f1/#dddddd` 四段面 |
| 卡片 | `transparent`、无框无影 | 面色卡 | 无框无影 |
| 圆角 | 0（只有日历圆） | 5px | 0 或 5px |
| 字号 | 14 正文 / h2 20 | 15 正文 / h1 27 | 16 正文 / h1 44 |
| 容器 | 960 | — | 1200 |
| 导航 | **动词**（訪ねる/学ぶ/参加する） | — | 4 项 |

**教训（我犯的，逐条记下）**：

1. **"素"的解不是加纹理，是版面结构 + 编辑层级。**
   我两次都答错了：第一次做成无菌白纸（素、空），
   第二次往地上糊四层纹理（浑、脏、装饰抢戏）。
2. **地色必须是平的。** 三家没有一家给页面地加材质。
   地和内容抢注意力时，读者分不清哪个是信息、哪个是装饰。
3. **层次靠面色浓淡 + 1px 罫，不靠阴影。** 一屏十几个浮块，页面就吵。
4. **有彩色要少。** 中之岛 0 个，另两家各 1 个。
   我用了骨/朱砂/青铜/拓黑/骨斑/绿/蓝一大把。
5. **密度有上限。** "首屏排十一件展品，安静的调性一下散了"。
   153 张铺成 11 列整面墙是**过**，不是大胆。
   正解：按真实档位**分组** + 组间留大空 + 每张给足白边。
6. **别"盒子套盒子"。** 浅色版面里再放同色卡片+边框，层次反而糊。
   玩法卡 / 每日一字 / 我的收集都已退成透明分栏 + 1px 上罫。
7. **装饰性小纹样（兆纹小波浪那种）是噪音。** 题材好不代表用法对；
   兆该当**结构**（真的按兆裂劈版面），不是描在罫线上的 12px 花边。

#### 现在长什么样

- 地：平的骨色 `#f2e8d5` + 一层极淡纸纹（`--fiber`）
- 内容版：`.sheet` 浅色纸面 + 1px 中性灰罫，无 clip-path、无内圈线
- 分区：`--rule` 1px 罫；悬停反馈靠**颜色**（朱砂）而不是位移+阴影
- 图鉴：**分组拓片集**——构件 37 / 合体字 34 / 王邑实物 61 / 讨伐字形 21，
  每组一个标题 + 条数，组间 `--s-9` 大空
- 拓片：`.ac-ob` 墨底承载，**卡身透明**（墨是落在纸上的一个印，不是网页盒子）

**「六」里剩下的活**：钻凿作边饰、卜辞体制（前辞/命辞/占辞/验辞）、
图鉴详情浮层与说明页也走拓片语言。**做之前先读上面那几份规范。**

---

## 7. 关键文件地图

```
index.html                壳（顶栏 + #sceneRoot + 页脚；脚本按序引入）
css/
  theme.css               设计令牌 + 通用组件 + 弹窗 + 状态提示   ← 改样式优先这里
                          （令牌有两处：:root 与 html[data-theme="bone"]，都要改）
  ui.css                  壳层布局：首页/图鉴/说明/展板/成就/页脚  ← 页面样式改这里
  app.css                 旧单文件版遗留（构件格、比分板、棋盘）
  modes.css               三个玩法各自的界面 + **字形线宽口径**（.ac-glyph path 等）
js/core/
  build.js                启动：品牌字形、**底纹生成 buildPatternURI()**、外观
  shell.js                路由 + 全部页面场景（~1077 行）  ← 页面结构改这里
  motion.js               滚动显现 / 字形描绘 / 底纹视差
  atlas.js                图鉴数据层（合并三个玩法的进度）
  achievements.js         成就与评级
  modes.js                模式注册表（register 只复制白名单字段！）
  leveldata.js            glyphSvg / glyphStrokeSvg / glyphStrokes
  _data.js                73 字形的几何（由 dev/_gen_glyph_parts.py 生成，勿手改）
  data.js / packs.js      构件池、字卡、内容包
js/modes/                 bone-build.js / wangyi-map.js / boss-raid.js
assets/                   oracle-bone.jpg(首页骨片照) wangyi-map.jpg(旧版 Agnes 底图)
                          wangyi-atlas.svg(当前原创王邑总图) guibao-front/side/back.png(龟宝设定图)
                          paper.png(纸纹，浅色面上用) bone.png(骨材质，页底用)
dev/                      51 个自查工具（见「五」）
README.md                 给读者看的项目文档（含素材授权、设计令牌说明）
```

**产物代码行数**（index.html + css×4 + js）：**8105 行 / 19 个文件**。
（先前记的 9082 是错的，实测口径就是这个；以后以实测为准。）

**模式契约**：`App.modes.register({id,name,tagline,desc,icon,accent,tags,minPlayers,maxPlayers,status,layout,data,settings,mount,unmount})`
`layout:'wide'` → 壳层给 `.app-shell` 加 `.layout-wide`。**`register()` 只复制列出的字段**，漏掉的键读不到。

**存储**：`App.store`，前缀 `ziqu.`，全包 try/catch。
`ziqu.wangyi` `{done:{分区:[字]}}` · `ziqu.bossraid` `{cleared:[],perfect:[]}` · `ziqu.bonebuild` `{done:[字]}` · `ziqu.achieved` `[]`

---

## 7.5 本次会话做完的与没做的（诚实交代）

**做了**：撤回绿金版（存成 tag）→ 生成骨材质 → 页底三层背景 → 刻辞加深 →
图鉴 153 张改拓片集 → `.sheet` 改骨版残边 → 兆纹分区线 → 全套验证 + 桌面/手机截图。

**验证结果**：语法、引用（18）、八个页面、壳层、构字、王邑、讨伐、手机端（390 无横向溢出）、
四个 CSS 花括号配平——**全绿**。对比度只剩基线那 1 对（`--edge` on `--bone`，非文字，
数值由 1.53 提到 2.02，是**有意的**：原来那个描边几乎看不见，骨面上的刻线本就该读得出来）。

**没做 / 不确定**：
- 第 4、6 条设计（钻凿、卜辞体制）没动。
- **图鉴详情浮层**、说明页、设置页仍是原来的浅色纸面，没跟着走拓片语言。
- **首页首屏大图**（`hero`）被 `sheetWrap(wrap, hero)` 排除在骨版外，仍是满幅——这是有意的。
- `.ac-rub` 那行"朱笔今字"是**新增元素**，用户还没看过，可能要说不要。
- `dev/_probe_point.py` 目前不可靠（页面常停在 394px），别依赖它。
- 未推送（等用户说"推"）。

---

## 8. 建议的第一步

**不要再从"撤回绿金版"开始了——那件事本次已经做完**（tag `wip-jade-gold-rejected` 就是那版）。
接手的第一件事应该是**先把成果给人看**：

```powershell
cd C:\DSH\字趣
# 起预览（端口占用就往上找），然后逐页看：
#   #/home   ← 骨材质底 + 刻辞 + 兆纹分区线
#   #/atlas  ← 拓片集（本次最大的改动）
python -m http.server 8099
```

```powershell
# 或者直接出图给人看
$py='C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
& $py dev\_route_shot.py atlas 1440 1000 _check\atlas.png 0
& $py dev\_route_shot.py home  1440 1000 _check\home.png  1250
& 'C:\Users\32058\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe' dev\_mobile.js "http://127.0.0.1:8099/index.html#/atlas" 390 844 _check\m_atlas.png
```

**等用户对"拓片集"这一版表态**，再决定往下做哪一条——不要自己一口气把「六」剩下的都铺开。
用户会明确说"好"或"还是素"。若说还是素，下一步最有把握的是第 4 条（钻凿作边饰）
与"图鉴详情浮层也走拓片／卜辞体制"。

**别一次改十个地方。改完跑「五」的全套，截图给人看。**

---

## 9. 与人协作的注意

- 用户会**贴 PPT / 图片**给参考。**先看清它到底在教什么**（这次教的是"要有密度、要大胆"），
  **不要照抄它的外形**——那会被直接指出"你就只会抄吗"。
- 汇报里要写：**改了什么文件、怎么预览、测了什么、哪些没测**。用户要证据，不要形容词。
- 不确定就问，但**别问能自己查出来的事**。
