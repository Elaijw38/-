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


def normalize(svg_text, name):
    """取出 path 数据，按真实包围盒等比缩放并居中到 CANVAS 画布。"""
    vb = re.search(r'viewBox="([^"]+)"', svg_text)
    paths = re.findall(r"<path\s+d=\"([^\"]+)\"", svg_text)
    if not paths:
        return None, None
    d = " ".join(paths)
    bb = path_bbox(d)
    if not bb:
        return None, None
    x0, y0, x1, y1 = bb
    w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
    inner = CANVAS - PAD * 2
    k = inner / max(w, h)                     # 等比缩放：长边撑满
    tx = PAD + (inner - w * k) / 2 - x0 * k   # 居中
    ty = PAD + (inner - h * k) / 2 - y0 * k
    # 用 g 承载变换，保留原始 path 数据，便于日后改渲染方式
    body = ('<g transform="translate({:.3f},{:.3f}) scale({:.5f})">'
            '<path d="{}" fill="none" stroke="{{C}}" stroke-width="{:.3f}" '
            'stroke-linecap="round" stroke-linejoin="round"/></g>'
            ).format(tx, ty, k, d, 0.9 / k)
    return body, (x0, y0, x1, y1)


def main():
    labels = json.loads(io.open(LABELS, "rb").read().decode("utf-8"))
    byid = {r["glyph_id"]: r for r in labels}

    # 汇总所有要收录的字，并记下它属于哪些区块
    wanted = {}          # name -> glyph_id
    zones = {}           # name -> [zone, ...]
    for name, gid in PIECES.items():
        wanted[name] = gid
        zones.setdefault(name, []).append("parts")
    for zone, table in EXTRA.items():
        for name, gid in table.items():
            if name not in wanted:
                wanted[name] = gid
            if zone not in zones.setdefault(name, []):
                zones[name].append(zone)
    for name, info in FALLBACK.items():
        wanted[name] = info["glyph_id"]

    items, missing = {}, []
    for name, gid in wanted.items():
        f = os.path.join(SVG_DIR, "%04d.svg" % gid)
        if not os.path.exists(f):
            missing.append((name, gid, "文件不存在"))
            continue
        body, bb = normalize(read(f), name)
        if body is None:
            missing.append((name, gid, "无法解析 path"))
            continue
        rec = byid.get(gid, {})
        items[name] = {
            "glyphId": gid,
            "svg": body,
            "bbox": [round(v, 3) for v in bb],
            "sourceChar": rec.get("modern_char"),
            "unicode": rec.get("unicode"),
            "charForm": rec.get("char_form"),
            "zones": zones.get(name, []),
        }
        if name in FALLBACK:
            items[name]["fallbackNote"] = FALLBACK[name]["note"]
            items[name]["isFallback"] = True

    # 按区块提供索引，前端不必自己筛
    zoneIndex = {}
    for name, zs in zones.items():
        for z in zs:
            zoneIndex.setdefault(z, []).append(name)
    for z in zoneIndex:
        zoneIndex[z].sort(key=lambda n: wanted.get(n, 9999))

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
        "zones": zoneIndex,
    }
    out = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    io.open(OUT_JSON, "w", encoding="utf-8").write(out)

    print("已写出:", os.path.normpath(OUT_JSON))
    print("字形总数: %d  体积: %.1f KB" % (len(items), os.path.getsize(OUT_JSON) / 1024))
    for z in sorted(zoneIndex):
        print("  区块 %-10s %d 个字形" % (z, len(zoneIndex[z])))
    if missing:
        print("!! 缺失:")
        for n, g, why in missing:
            print("   %s (glyph_id %s) %s" % (n, g, why))


if __name__ == "__main__":
    main()
