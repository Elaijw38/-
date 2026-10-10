# 字趣 · 甲骨构字记

一个以甲骨文为题材的**汉字文化游戏平台**。
首个玩法「甲骨构字」已上线：翻出契文，用甲骨文构件拼出它，在卜问与质问里读懂商代。

> 本项目前身是单文件原型《字从契来》。现按平台化思路重构：
> **新玩法是一个模块文件，不改动平台其余部分。**

---

## 这是什么

| | |
|---|---|
| **形态** | 纯静态网页（H5）。无需服务器、无需构建、无需数据库 |
| **运行** | 双击 `index.html` 即可本地打开；上传到任意静态托管即可在线访问 |
| **数据** | 全部保存在本机浏览器（`localStorage`），**不上传任何服务器** |
| **依赖** | 零。没有框架、没有 CDN、没有外部字体与图片 |

**为什么不用 ES module**：`import` 在 `file://` 下会被浏览器的 CORS 策略拦住，
必须起服务器才能调试。这里改用传统 `<script>` + 全局命名空间 `App`，
**既能拆文件、又能双击打开、还能直接传 GitHub Pages。**

---

## 目录

```
字趣/
├─ index.html              壳层（站点头 / 场景挂载点 / 页脚署名 / 脚本加载顺序）
├─ css/
│  ├─ app.css              原型的原有样式（保留）
│  ├─ theme.css            设计令牌（外观固定骨白；zhuogu/plain 变量保留备查）
│  ├─ ui.css               壳层组件：站点头、首页卡、模式卡、响应式
│  └─ modes.css            玩法层：对局界面、构件台、放置槽、复盘
├─ js/
│  ├─ core/
│  │  ├─ data.js           内置数据（构件、字卡、卜问）
│  │  ├─ levels.json       ★ 王邑地图关卡数据（区块 / 关卡 / 解锁规则）
│  │  ├─ glyph-parts.json  ★ 甲骨字形映射（dev/_gen_glyph_parts.py 生成）
│  │  ├─ _data.js          ★ 上面两个 JSON 的内联版（dev/_build_leveldata.py 生成）
│  │  ├─ leveldata.js      暴露为 App.levels / App.glyphs
│  │  ├─ util.js           DOM 简写、存储封装、图片缩放、事件总线
│  │  ├─ packs.js          通用内容包（多类型：字包 / 题库 / 图鉴 / 章节）
│  │  ├─ modes.js          模式注册表 —— 可插拔点
│  │  ├─ shell.js          路由与壳层（首页 / 玩法列表 / 设置 / 筹备中）
│  │  └─ build.js          启动：注入品牌字形、套用外观、启动路由
│  └─ modes/
│     ├─ bone-build.js     玩法：甲骨构字（单字选构）
│     └─ wangyi-map.js     玩法：殷商王邑（关卡地图）
├─ dev/                    开发自查脚本（不进部署）
├─ README.md
└─ LICENSE
```

> ★ 标记者为「王邑闯关」新增。**改关卡内容只需改 `levels.json`**，
> 改完务必跑 `python dev/_build_leveldata.py` 重新内联，否则页面读到的还是旧数据。

---

## 玩法二：殷商王邑（关卡地图）

一张地图分区块，逐块收复。规则与内容全在 `js/core/levels.json`，代码不写死关卡。

| 区块 | 难度 | 机制 | 说明 |
|---|---|---|---|
| 自然风光 | 初级 | `boss` 拆字 | 给甲骨字形，四选一认出是哪个构件 |
| 动植物 | 中级 | `pair` 配对 | 甲骨形 ←→ 今字，左右点选配对 |
| 中央占卜坑 | 终极 | `pair` 综合 | 全字域配对 |
| 生产生活 | 高级 | `oracle` 卜辞 | **素材待补**，暂不开放 |
| 单字选构练习 | 侧边 | `practice` | 跳回原有玩法，保留原入口 |

**解锁规则**：区块声明 `unlocked:true`（默认开放）或 `unlock:{after,need}`
（通关某区块 N 关后解锁）；`comingSoon:true` 一律不开放。
进度存 `ziqu.wangyi`，地图底部可重置。

**点亮**：已解锁区块高亮（`.wy-cell.on`），未解锁压暗去饱和（`.wy-cell.off`）。
按需求**先只做静态高亮，动效延后**。

### 卜辞素材的缺口（待补）

生产生活区块的高级玩法需要**甲骨卜辞文本**，但现有素材里没有：
`_provenance.jsonl` 只有字形元数据，`data.js` 的 `src` 仅 7 条零散卜辞。
**不编造卜辞**（学术项目），故该区块结构已建好、内容空缺，标 `comingSoon`。
取得素材后填入该区块的 `levels` 数组即可，代码无需改动。

---

## 部署

**只需要上传整个目录**（不是单个文件——这是多文件架构，便于后续扩展）。

### GitHub Pages（当前线上方式）

```bash
git clone https://github.com/Elaijw38/jiagugouciji.git
cd jiagugouciji
# 把 index.html、css/、js/ 等放入后
git add .
git commit -m "更新说明"
git push
```

站点地址：**https://elaijw38.github.io/jiagugouciji/**

> 仓库曾用名 `-`，2026-10 改名为 `jiagugouciji`。
> 旧地址 `…github.io/-/` 由 GitHub 301 重定向到新地址，已发出的链接仍可打开。
> 本地仓库若仍指向旧地址，执行一次
> `git remote set-url origin https://github.com/Elaijw38/jiagugouciji.git` 即可。

**更省事的日常更新**：直接运行仓库根目录的 `deploy.ps1`（右键 → 使用 PowerShell 运行），
它会自动提交并推送，遇到历史分叉会询问是否覆盖。

> ⚠️ 上传时务必把 `index.html`、`css/`、`js/` **一起**放到仓库根目录；
> 只传 `index.html` 会导致样式与脚本 404，页面白屏（见文末排查）。

### 其他托管

| 平台 | 说明 |
|---|---|
| **Vercel / Netlify / Cloudflare Pages** | 拖入整个目录即可，自动 HTTPS |
| **Gitee Pages / 腾讯云静态托管** | 国内访问快；自有域名 + 大陆服务器**通常需 ICP 备案** |
| **校园网 / 学院服务器** | 最省事，但可能限制外网访问 |

### 部署后的检查

| 检查 | 怎么看 |
|---|---|
| 首页能开 | 看到「字趣」站点头与三张功能卡 |
| HTTPS 生效 | 地址栏有小锁（**非 HTTPS 时部分浏览器能力受限**） |
| 走一局 | 开始玩 → 甲骨构字 → 选难度 → 开始 → 拼字提交（按钮是「契刻」） |
| 看得分 | 比分板上是「甲骨片 ×N」，不是裸数字 |
| 双人质问 | 模式选「双人对战」，拼对后会出现质问按钮 |
| 扫码打开 | 把链接生成二维码扫一下 |

### 白屏排查（线上打开是空白）

**症状**：页面标题正常，但正文区全空，只有页脚文字。

**原因**：只上传了 `index.html`，`css/` 与 `js/` 没传 → 样式与脚本 404。

**30 秒确认**：在地址栏直接访问 `https://<站点>/css/theme.css`。
返回 404 即为本条；返回 CSS 文本则说明资源在，问题在别处。

**对照检查**（GitHub Pages 跑在 Linux 上，**大小写敏感**，Windows 本地不敏感）：

| 要点 | 正确 | 错误示例 |
|---|---|---|
| 顶层必须有三个 | `index.html` `css/` `js/` | 只有 `index.html` |
| 目录名全小写 | `css` `js` | `CSS` `JS` `Js` |
| 层级不能多一层 | 根目录直接是这三个 | 套了 `字趣/` 或 `src/` 一层 |
| 站点路径 | `elaijw38.github.io/jiagugouciji/` | 误用旧地址 `…github.io/-/`（会重定向，但别写进材料） |

---

## 玩法模块的约定

新增玩法**只需新建一个文件**，放在 `js/modes/` 下，并在 `index.html` 里加一行 `<script>`。

```js
App.modes.register({
  id: 'your-mode',
  name: '玩法名',
  tagline: '一句话说明',
  desc: '展开说明',
  icon: '单',                 // 单字图标
  accent: 'var(--cinnabar)',  // 图标底色
  tags: ['单人', '计时'],
  minPlayers: 1, maxPlayers: 2,
  status: 'ready',            // ready（可玩）| wip（开发中）| planning（筹备中）

  data: {                     // 需要哪些数据，平台会准备好
    packs: [{ type: 'cards', role: 'main', label: '字包' }],
    assets: []
  },

  settings: [],               // 可选设置项声明（也可以自己在 mount 里画）

  // 平台给你一个空容器 host，以及一份上下文 ctx
  mount: function (host, ctx) {
    // ctx.primaryPack  已解析好的主数据包
    // ctx.packs        该模式可用的全部包
    // ctx.ui           共享渲染工具（el / esc / toast / signed …）
    // ctx.store        命名空间化存储
    // ctx.theme        读写主题
    // ctx.nav          跳转（home / modes / replay）
  },

  unmount: function (host) { /* 清定时器、移除 body 上的临时类 */ }
});
```

**平台保证**：
- 模式之间互不干扰（各自 `mount`/`unmount`，不共享全局状态）
- 离开对局时自动调用 `unmount`
- 内容包按模式声明的类型自动解析，模式不必了解存储细节

---

## 内容包（多类型）

平台不只服务「字包」。`js/core/packs.js` 里登记了四类结构，新类型加一条 schema 即可：

| 类型 | 结构 | 用途 |
|---|---|---|
| `cards` | `{ pieces:[], cards:[] }` | 字包（构件 + 字卡） |
| `quiz` | `{ questions:[] }` | 题库 |
| `atlas` | `{ entries:[] }` | 图鉴 |
| `script` | `{ chapters:[] }` | 剧本 / 章节 |

用户自建内容保存在 `localStorage`，可导出为 JSON 分发与备份。

---

## 设计与素材

### 视觉取向

参考《黑神话：悟空》一类"厚重东方 + 现代游戏感"的处理手法（深色底、材质层次、
雕刻感描边、戏剧性明暗对比），**但颜色与纹样一律回到甲骨本身**：

| 依据 | 用在哪 |
|---|---|
| **墨** `#1b1611` | 刻痕、正文 |
| **骨** `#efe4cd` | 载体、亮面 |
| **朱砂** `#a8321f` | 点睛、强调、主按钮（取自甲骨卜辞的"填朱"） |
| **青铜** `#8a6a33` | 少量点缀、描边 |
| **兆纹** `#8a7a5e` | 裂纹、分隔线 |
| 骨片轮廓（不规则八边） | 编号牌、放置槽、构件格 |

三套主题：**灼骨**（默认，深色）· **骨白**（浅色，出土本色）· **素色**（无纹理，阅读优先）。

### 字形素材与授权

页面背景纹样与标题字形来自 **真实甲骨文字形**：

- 数据集：[hanzi-glyphs-svg](https://github.com/zhouyongh/hanzi-glyphs-svg)
- 上游：Li, Qing-sheng & Bian, Yu-lin (2026),
  *Oracle Bone Glyphs: Parametric Vector Dataset (v0.3)*,
  [10.5281/zenodo.22467946](https://doi.org/10.5281/zenodo.22467946)
- 授权：**CC BY 4.0** —— 允许商用，**须署名**
- 本项目所做的修改：缩放、配色、合成为平铺纹样、编排为标题字形

署名已写入 `index.html` 页脚，**请勿删除**（这是授权条件）。

### 构件字形：`js/core/glyph-parts.json`

**61 个甲骨字形**，供拼字/拆字/配对三个玩法使用，同样出自上面这份数据集，
**CC BY 4.0，须署同一作者**。

- 内容：字 → `{glyphId, svg, bbox, sourceChar, unicode, zones}`，SVG 内联（避免额外请求与 file:// 跨域）
- 分区索引：`zones` 字段按 `parts` / `landscape` / `creature` / `life` / `center` 分组，前端不必自己筛
- 画布：统一归一化到 100×100，按每个字形的实际路径坐标等比缩放并居中
- 署名与来源写在 JSON 的 `attribution` 字段里，随数据一起带走
- **重新生成**：`python dev/_gen_glyph_parts.py <上游稀疏检出目录>`
  上游仓库：`github.com/aylqs2025/oracle-bone-jgw-1203`（commit `5496ad5`）

已核对的两个坑：

| 构件 | 情况 |
|---|---|
| 门 / 贝 | 数据集以**繁体「門」「貝」**收录（glyphId 849 / 481），需按繁体查 |
| 囗 | 数据集**未收录**，但**不参与任何字卡**；借用「口」的方框形，JSON 内标 `isFallback` |

> 特别提醒：**不要手工编辑 `glyph-parts.json`**（文件首行已注明）。
> 它由脚本生成，手改会在下次重新生成时被覆盖。

---

## 开发自查

`dev/` 与根目录的 `_check*.py`、`_shots.py` 等脚本用于**在真实浏览器里验证**：

| 脚本 | 作用 |
|---|---|
| `_run_drive.py` + `_check/drive.js` | 在 headless Edge 里走一遍全流程，回报状态与控制台错误 |
| `_shots.py` | 截图各页面，用于人工检查观感 |
| `_bg_final.py` / `build_ob_bg.py` | 由真实字形合成背景纹样 |

> 这些脚本依赖本机的 Microsoft Edge 与 bundled Python，**不属于部署内容**，
> 上传时可整个排除。

---

## 已知限制

- **字体**：正文用系统宋体系列（Songti SC / Noto Serif SC / SimSun）。
  若目标设备缺字体会退化到默认衬线，观感略有差异。
- **浏览器能力**：标题的墨色渐变用 `background-clip: text`，
  已提供 `@supports` 降级；不支持时退回纯墨色。
- **存储上限**：`localStorage` 约 5MB。图片素材多时请及时导出备份。
- **未做后端**：无账号、无云同步、无排行榜。跨设备需手动导出／导入。
