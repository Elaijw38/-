# -*- coding: utf-8 -*-
"""开发脚本共用：从 glyph-parts.json 的记录重建整字 SVG。

为什么需要它：JSON 里**不再存**整段 svg（它等于 transform + 各笔画 d，
存两份会让体积翻倍：实测 157KB → 315KB）。前端由 leveldata.js 重建，
这边的开发脚本也要按同一规则重建，否则读不到字形。
"""


def build_svg(rec, color="currentColor"):
    """rec 是 glyph-parts.json 里 parts[字]；返回可内联的 <g>…</g>"""
    if not rec:
        return ""
    pieces = rec.get("pieces") or []
    if not pieces:
        return ""
    d = " ".join(p["d"] for p in pieces)
    return ('<g transform="%s"><path d="%s" fill="none" stroke="%s" '
            'stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/></g>'
            % (rec["transform"], d, color, rec["strokeWidth"]))
