# -*- coding: utf-8 -*-
"""
生成 js/core/glyph-parts.json —— 37 个构件的甲骨字形映射。

素材来源（均为 CC BY 4.0）：
  Qing-sheng Li and Yu-lin Bian. An Interpretable Parametric Representation
  and Open Dataset for Oracle Bone Script: Adaptive Arc Segmentation and SVG
  Resource. npj Heritage Science (2026).
  数据集：Oracle Bone Glyphs: Parametric Vector Dataset (v0.3)
  DOI 10.5281/zenodo.22467946 · 镜像 github.com/aylqs2025/oracle-bone-jgw-1203

本脚本把用到的 37 个 SVG 归一化（统一画布、按实际坐标居中）后内联进 JSON，
这样前端无需再发请求、也不会有 file:// 下的跨域问题。

用法：
  python dev/_gen_glyph_parts.py                # 从 C:\\DSH\\_ob_src 读取
  python dev/_gen_glyph_parts.py <源目录>        # 或指定稀疏检出目录
"""
import io, json, os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\DSH\_ob_src"
SVG_DIR = os.path.join(SRC, "data", "svg_parametric")
LABELS = os.path.join(SRC, "data", "jgw_1203_labeled.json")
REPO = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(REPO, "..", "js", "core", "glyph-parts.json")

# 构件名 -> glyph_id（由 Unicode 匹配得到；门/贝 数据集以繁体收录）
# 收录的字，按用途分组：
#   parts    —— 拼字玩法所需的 37 个构件（键名即构件名）
#   landscape—— 自然风光区块（初级拆字）
#   creature —— 动植物区块（中级配对）
#   life     —— 生产生活区块（高级，卜辞素材待补，字形先备齐）
#   center   —— 中央占卜坑（终极综合）
PIECES = {
    "日": 495, "月": 515, "雨": 829, "水": 772, "火": 732, "山": 678,
    "田": 979, "木": 428, "人": 585, "大": 747, "女": 867, "子": 1037,
    "目": 259, "耳": 850, "口": 75, "又": 196, "止": 97, "牛": 67,
    "羊": 287, "犬": 720, "豕": 691, "隹": 273, "鱼": 1097, "禾": 536,
    "屮": 36, "宀": 549, "门": 849, "酉": 1051, "斤": 994, "戈": 908,
    "矢": 402, "糸": 941, "力": 986, "贝": 481, "舟": 636, "卜": 250,
}

EXTRA = {
    "landscape": {   # 自然风光
        "土": 970, "石": 684, "川": 819, "泉": 824, "丘": 621, "谷": 826,
    },
    "creature": {    # 动植物
        "林": 458, "竹": 336, "米": 545, "虎": 368, "鹿": 710, "虫": 955,
    },
    "life": {        # 生产生活
        "足": 137, "刀": 320, "斧": 995, "弓": 934, "衣": 627,
        "皿": 370, "鼎": 533, "缶": 401, "玉": 32, "井": 384, "邑": 490, "郭": 408,
    },
    "center": {      # 中央占卜坑
        "大": 747, "又": 196, "止": 97, "子": 1037, "口": 75, "目": 259,
    },
}
# 数据集未收录「囗」，但它不参与任何字卡，用「口」的字形作方框代用
FALLBACK = {"囗": {"glyph_id": 75, "note": "数据集未收录「囗」；借用「口」的方框形，不参与任何字卡"}}

# BOSS 战专用的繁复字形：笔画段数多（9~17 段），用于「笔画终局」——
# 全身是连续纹路护甲，一段一段斩断。段数实测见 dev/_boss_probe.py。
# 只做字形，不进地图，也不进「甲骨构字」的构件台。
BOSS = {
    "車": 1000,   # 17 段
    "舞": 424,    # 16 段
    "龜": 962,    # 14 段
    "馬": 702,    # 12 段
    "龍": 843,    # 9 段
    "鼓": 361,    # 11 段
    "鳥": 296,    # 11 段
    "爵": 1188,   # 10 段
    "彝": 952,    # 10 段
    "尊": 1054,   # 10 段
    "絲": 953,    # 10 段
    "象": 701,    # 6 段
}
CANVAS = 100.0     # 统一画布边长（viewBox 单位）
PAD = 5.0          # 四周留白


def read(path):
    return io.open(path, encoding="utf-8").read()


def path_bbox(d):
    """解析 SVG path 的绝对坐标，求包围盒（数据里用的是绝对命令）。"""
    xs, ys, cur = [], [], [0.0, 0.0]
    # 抓出所有「命令字母 + 数字串」
    for m in re.finditer(r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)", d):
        cmd, argstr = m.group(1), m.group(2)
        nums = [float(x) for x in re.findall(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?", argstr)]
        if cmd in "MmLl":
            for i in range(0, len(nums) - 1, 2):
                if cmd == "m" and cur != [0.0, 0.0]:
                    cur = [cur[0] + nums[i], cur[1] + nums[i + 1]]
                else:
                    cur = [nums[i], nums[i + 1]]
                xs.append(cur[0]); ys.append(cur[1])
        elif cmd in "Hh":
            for v in nums:
                cur = [cur[0] + v if cmd == "h" else v, cur[1]]
                xs.append(cur[0]); ys.append(cur[1])
        elif cmd in "Vv":
            for v in nums:
                cur = [cur[0], cur[1] + v if cmd == "v" else v]
                xs.append(cur[0]); ys.append(cur[1])
        elif cmd in "Cc":
            for i in range(0, len(nums) - 5, 6):
                xs += [nums[i], nums[i + 2], nums[i + 4]]
                ys += [nums[i + 1], nums[i + 3], nums[i + 5]]
                cur = [nums[i + 4], nums[i + 5]]
        elif cmd in "SsQq":
            for i in range(0, len(nums) - 3, 4):
                xs += [nums[i], nums[i + 2]]
                ys += [nums[i + 1], nums[i + 3]]
                cur = [nums[i + 2], nums[i + 3]]
        elif cmd in "Tt":
            for i in range(0, len(nums) - 1, 2):
                xs.append(nums[i]); ys.append(nums[i + 1])
                cur = [nums[i], nums[i + 1]]
        elif cmd in "Aa":
            for i in range(0, len(nums) - 6, 7):
                xs.append(nums[i + 5]); ys.append(nums[i + 6])
                cur = [nums[i + 5], nums[i + 6]]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def split_strokes(d):
    """把 path 数据按 M 起点切成独立笔画。

    数据集里 61/61 全部只用绝对 M/L 命令，所以按 'M' 切是安全的：
    每段就是一条折线，正好对应书写的一笔。
    """
    segs = []
    for seg in re.split(r"(?=\bM\s)", d.strip()):
        seg = seg.strip()
        if seg.startswith("M") and len(seg) > 8:
            segs.append(seg)
    return segs or ([d.strip()] if d.strip() else [])


def normalize(svg_text, name):
    """取出 path 数据，按真实包围盒等比缩放并居中到 CANVAS 画布。

    同时把该字拆成笔画（pieces），每笔带上【画布坐标系】里的包围盒，
    供「拖拽构字」用：部件在池子里按自身包围盒单独显示，
    落回目标时用同一个画布坐标系就位。
    """
    vb = re.search(r'viewBox="([^"]+)"', svg_text)
    paths = re.findall(r"<path\s+d=\"([^\"]+)\"", svg_text)
    if not paths:
        return None, None, None
    d = " ".join(paths)
    bb = path_bbox(d)
    if not bb:
        return None, None, None
    x0, y0, x1, y1 = bb
    w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
    inner = CANVAS - PAD * 2
    k = inner / max(w, h)                     # 等比缩放：长边撑满
    tx = PAD + (inner - w * k) / 2 - x0 * k   # 居中
    ty = PAD + (inner - h * k) / 2 - y0 * k
    sw = 0.9 / k
    # 用 g 承载变换，保留原始 path 数据，便于日后改渲染方式
    body = ('<g transform="translate({:.3f},{:.3f}) scale({:.5f})">'
            '<path d="{}" fill="none" stroke="{{C}}" stroke-width="{:.3f}" '
            'stroke-linecap="round" stroke-linejoin="round"/></g>'
            ).format(tx, ty, k, d, sw)

    # ---- 拆笔画：每笔给出画布坐标系的包围盒 ----
    pieces = []
    for seg in split_strokes(d):
        sb = path_bbox(seg)
        if not sb:
            continue
        cx0 = tx + sb[0] * k
        cy0 = ty + sb[1] * k
        cx1 = tx + sb[2] * k
        cy1 = ty + sb[3] * k
        pieces.append({
            "d": seg,
            "c": [round(cx0, 2), round(cy0, 2), round(cx1, 2), round(cy1, 2)],
        })
    meta = {
        "transform": "translate({:.3f},{:.3f}) scale({:.5f})".format(tx, ty, k),
        "strokeWidth": round(sw, 4),
        "pieceCount": len(pieces),
        "pieces": pieces,
    }
    return body, (x0, y0, x1, y1), meta


def main():
    labels = json.loads(io.open(LABELS, "rb").read().decode("utf-8"))
    byid = {r["glyph_id"]: r for r in labels}

    # 汇总所有要收录的字。
    # 注意：**不做分区索引**。早先曾按「区块」给字分组（landscape/creature/life），
    # 但那是按「单构件字」的思路建的；后来关卡改为「单字拆字」，同一个字
    # （如 日、月）既是自然风光的目标、又是拆字的构件，分组就与实际内容脱节，
    # 还让拆字的干扰项抽不到同域的字。故只保留一张统一字表 parts，
    # 具体哪些字用于哪一关，由 levels.json 决定（内容与代码分离）。
    wanted = {}
    for name, gid in PIECES.items():
        wanted[name] = gid
    for table in EXTRA.values():
        for name, gid in table.items():
            wanted.setdefault(name, gid)
    for name, gid in BOSS.items():
        wanted.setdefault(name, gid)
    for name, info in FALLBACK.items():
        wanted[name] = info["glyph_id"]

    items, missing = {}, []
    for name, gid in wanted.items():
        f = os.path.join(SVG_DIR, "%04d.svg" % gid)
        if not os.path.exists(f):
            missing.append((name, gid, "文件不存在"))
            continue
        body, bb, meta = normalize(read(f), name)
        if body is None:
            missing.append((name, gid, "无法解析 path"))
            continue
        rec = byid.get(gid, {})
        items[name] = {
            "glyphId": gid,
            # 不存整段 svg：它等于 "transform + 各笔画 d"，存两份会让
            # 文件体积翻倍（实测 157KB → 315KB）。前端按
            # transform/strokeWidth/pieces 重建，见 leveldata.js 的 glyphSvg。
            "bbox": [round(v, 3) for v in bb],
            "sourceChar": rec.get("modern_char"),
            "unicode": rec.get("unicode"),
            "charForm": rec.get("char_form"),
            # 笔画拆分：供「拖拽构字」把字打散成可拖的部件
            "transform": meta["transform"],
            "strokeWidth": meta["strokeWidth"],
            "pieceCount": meta["pieceCount"],
            "pieces": meta["pieces"],
        }
        if name in FALLBACK:
            items[name]["fallbackNote"] = FALLBACK[name]["note"]
            items[name]["isFallback"] = True

    doc = {
        "_generated": "由 dev/_gen_glyph_parts.py 生成，请勿手改",
        "canvas": CANVAS,
        "attribution": {
            "dataset": "Oracle Bone Glyphs: Parametric Vector Dataset (v0.3)",
            "authors": "Qing-sheng Li and Yu-lin Bian",
            "citation": ("Qing-sheng Li and Yu-lin Bian. An Interpretable Parametric "
                         "Representation and Open Dataset for Oracle Bone Script: "
                         "Adaptive Arc Segmentation and SVG Resource. "
                         "npj Heritage Science (2026)."),
            "license": "CC BY 4.0",
            "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
            "doi": "10.5281/zenodo.22467946",
            "mirror": "https://github.com/aylqs2025/oracle-bone-jgw-1203",
            "commit": "5496ad559f81ae8632f3915e8ec2beb705c64ba3",
            "modifications": ("按每个字形的实际路径坐标等比缩放、居中到统一画布，"
                              "描边改为 currentColor 以便跟随主题色；字形本身未改动"),
        },
        "parts": items,
    }
    out = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    io.open(OUT_JSON, "w", encoding="utf-8").write(out)

    print("已写出:", os.path.normpath(OUT_JSON))
    print("字形总数: %d  体积: %.1f KB" % (len(items), os.path.getsize(OUT_JSON) / 1024))
    if missing:
        print("!! 缺失:")
        for n, g, why in missing:
            print("   %s (glyph_id %s) %s" % (n, g, why))


if __name__ == "__main__":
    main()
