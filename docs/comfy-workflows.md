# 字趣 · ComfyUI 出图工作流记录

> 本文件是**可复现凭据**：提示词、负面提示词、尺寸、种子、工作流 JSON 全在
> `C:/DSH/comfy_assets/*/\_meta.json` 里（每条含完整 prompt 与 ComfyUI 工作流图）。
> 本文件只记方向、结论与待办。

---

## 一、环境

| 项 | 值 |
|---|---|
| ComfyUI | `C:\DSH\ComfyUI`（portable，自带 python_embeded 3.13.14 / torch 2.14.0+cu130） |
| 启动 | `C:\DSH\ComfyUI\run_nvidia_gpu.bat`，API 在 `http://127.0.0.1:8188` |
| 模型 | `sd_xl_base_1.0.safetensors`（SD1.5 也在，未用） |
| 模型目录 | `D:\ComfyUI-models`（经 `ComfyUI\extra_model_paths.yaml` 挂载） |
| GPU | RTX 4070 Laptop 8 GB |
| 自定义节点 | 只有 ComfyUI-Manager 与中文翻译包；本流程只用内置节点 |

**工作流只用内置节点**：`CheckpointLoaderSimple → CLIPTextEncode(x2) →
EmptyLatentImage → KSampler → VAEDecode → SaveImage`（refine 段换成
`LoadImage → ImageScale → VAEEncode → KSampler(denoise) → VAEDecode → SaveImage`）。

## 二、四个工具（都在 `tools/`）

| 脚本 | 作用 |
|---|---|
| `comfy_batch.py` | 批量出图；提示词/负面/尺寸/种子/工作流全写进 `_meta.json`；支持 base 与 refine 两段 |
| `comfy_finalize.py` | 定稿到项目规格（2624×1472 JPEG）＋ 出联系表 / 九宫切片自查图 |
| `comfy_finalize_boss.py` | Boss 定稿：抠纸底 → 透明 PNG（1024×1024，主体占比会在日志里量出来） |
| `comfy_compose.py` | 物件拼版：把物件图抠出来，按**指定坐标**贴进地图（坐标即热点坐标） |
| `gen_sheets_spec.py` / `gen_objs_one_spec.py` | 由脚本生成规格 JSON，避免手抄 40+ 条提示词 |

规格文件：`specs_maps_base*.json`、`specs_maps_refine.json`、`specs_finalize.json`、
`specs_boss_base.json`、`specs_boss_finalize.json`、`specs_objs_one.json`、`specs_compose_sky.json`。

## 三、美术方向（吸收五个参考的**气质**，不照搬）

参考：[数字敦煌](https://dlc.e-dunhuang.com/)、[清明上河图互动长卷](https://chinahall.fieldmuseum.org/interactive/qingming-scroll)、
[丝路山水地图](https://hk.science.museum/ms/silkroad2018/mb/eexhibits.html)、ArtWord 甲骨文项目、行旅图。

共同调性：**手绘水墨＋淡彩、暖黄褐与青玉的窄色域、细密笔触、旧绢底色、阴天漫射光**。
五张主题小地图靠**地貌与色温**区分，不靠边框与标签。Boss 沿用同一套水彩与描边，
只把性情换成威压（深底、窄色域、朱砂点睛）。

六张图与 Boss 都不出现任何文字、汉字、甲骨字形、数字、按钮、边框、路线标记、水印——
网页负责字形与交互提示。

## 四、实测结论（重要，下一轮直接照这条走）

1. **SDXL 画不了「一张图里排满几十个教学物件」。** 试过 4 轮、20 余张：
   把 30+ 物件写进提示词，结果必然是融合、丢失或画崩。
2. **「一格一个物件的 2×2 表」也不行。** 实测 `beast-a`（豕/犬/虎/虫）把犬和虎
   合成了一只奇美拉、豕与虫直接消失；`life-a`（缶/皿/酉/玉）画成一堆 8 个罐子。
   反例：单个器物表（陶缶等）反而很稳——**越少越准**。
3. **一张图只画一个物件**才是可靠的。所以缺的物件走 `specs_objs_one.json`
   （44 件单件出图）→ `comfy_compose.py` 按坐标贴回地图。
4. **低重绘放大（refine，denoise 0.32）只补笔触、不改构图**，所以热点坐标在
   放大前后不变——这是能放心用 1408×768 生成、再放大到 2624×1472 的前提。
5. SDXL 画中国画题材时爱在角落加**题款/印章**（实测出现在 life、beast 上）。
   负面提示词里必须逐项点名 `text, calligraphy, seal, signature, colophon…`。

## 五、六张地图的定稿来源（现状）

| 图 | 项目路径 | 生成源 | 种子 |
|---|---|---|---|
| 大地图 | `assets/level2-world.jpg` | `v4/world_850101_.png` | 850101 |
| 01 天象 | `assets/level2-01-sky.jpg` | `v3/sky_830102_.png` | 830102 |
| 02 山川 | `assets/level2-02-land.jpg` | `v4/land_850103_.png` | 850103 |
| 03 草木 | `assets/level2-03-plant.jpg` | `v4/plant_850104_.png` | 850104 |
| 04 禽兽虫鱼 | `assets/level2-04-beast.jpg` | `v4/beast_850105_.png` | 850105 |
| 05 人居器物 | `assets/level2-05-life.jpg` | `v4/life_850106_.png` | 850106 |

全部已按项目规格落成 **2624×1472 JPEG**（`tools/comfy_finalize.py --mode lanczos`）。
原始生成图留在 `C:/DSH/comfy_assets/`（v3、v4、boss、objs、one），随时可再定稿。

旧图在 git 里（`git show HEAD:assets/level2-world.jpg`），可回滚。

## 六、Boss（第三关，21 张）

`assets/boss-<拼音>.png`，1024×1024 透明底，`tools/comfy_finalize_boss.py` 产出。
对照图：`_check/sheet-boss.png`（第 1 格是龟宝，用来核协调度）。

**协调度结论**：Boss 与龟宝同属水彩纸面、细描边、暖光那一支，放在一起不打架；
差别在性情（龟宝可爱、Boss 威压）与明度（龟宝浅、Boss 深）。
待改：抠图的边缘还带着一圈浅色纸边（`sheet-boss.png` 里能看出来），
下一轮应把 `tol` 调大一点、羽化加到 2.5px，或改用「先压暗纸底再抠」。

## 七、覆盖情况与待办（**诚实记录**）

第二轮地图画得比第一轮好，但**它们本身只画出了教学对象的一部分**：
能一眼认出并可直接设热点的约 15 个（山川的峰与河、草木的树与竹、禽兽的鹿牛羊鱼隹、
人居的城郭门船与几个人物）。其余靠单件出图补齐。

- [x] 六张地图按规格替换（2624×1472 JPEG）
- [x] 21 张 Boss 形象透明 PNG
- [ ] **44 件单件物件出图**（`comfy_assets/one`，本轮进行中）
- [ ] **物件拼版贴回五张小地图**（`comfy_compose.py` + 各区 specs）
- [ ] **按新图重新校准 61 个热点**，并跑 `dev/_l2_overlay_new.py` 叠图核对
- [ ] 第三关战斗界面接入 Boss 立绘（`js/modes/boss-raid.js` 的 `bd-boss` 区块）
- [ ] 手机端复核热点是否点得中（`dev/_wy2_touchsize.py` / `_wy2_walkthrough.py`）

> 注意：**六张新图已经在 assets 里生效**，而 `levels.json` 的热点还是按旧图标的，
> 所以现在这一版的地图与新热点**尚未对齐**。在完成上面第 3、4 项之前，
> 第二关的热区位置是不准的——这一点必须在交付说明里讲清楚。

## 八、常用命令

```powershell
# 出图（base 段）
python tools\comfy_batch.py --spec tools\specs_objs_one.json --only o-hu,o-gui
# 放大到项目规格
python tools\comfy_finalize.py --spec tools\specs_finalize.json --mode lanczos
# 联系表 / 九宫切片（自查）
python tools\comfy_finalize.py --sheet C:/DSH/comfy_assets/one
python tools\comfy_finalize.py --slices assets\level2-05-life.jpg --slice-prefix life
# Boss 定稿
python tools\comfy_finalize_boss.py --spec tools\specs_boss_finalize.json
# 拼版（坐标即热点坐标）
python tools\comfy_compose.py --spec tools\specs_compose_sky.json
# 热点叠图核对
python dev\_l2_overlay_new.py
```
