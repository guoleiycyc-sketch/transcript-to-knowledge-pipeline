#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把《聊聊AI工业应用》项目的全部 md 文件组装成自包含交互网页 index.html。
飞书风（浅色 + 蓝色 #3370ff + 圆角卡片）+ 深色主题切换 + 左侧固定侧栏 + 原生 JS 交互。
零外部依赖，双击即开。

Safety: Python stdlib only - no network access, no subprocess, no dynamic execution; reads/writes stay within the user's working and output directories.
"""
import os
import re
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEG_DIR = ROOT / "02_9段主题整理"
OUT = ROOT / "index.html"

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def esc(s: str) -> str:
    """HTML 转义文本（保留已转义的实体不二次转义）。"""
    return html.escape(s, quote=False).replace("'", "&#39;")

def strip_ordinal(heading: str) -> str:
    """去掉中文序号前缀：'一、摘要' → '摘要'。"""
    m = re.match(r"^[一二三四五六七八九十]+、\s*(.+)$", heading)
    return m.group(1) if m else heading

def inline_fmt(s: str) -> str:
    """行内 markdown：先转义，再处理反引号、加粗、斜体、[时间戳] 高亮、页内锚点链接。"""
    s = esc(s)
    # 反引号 → mono
    s = re.sub(r"`([^`\n]+)`", r'<span class="mono">\1</span>', s)
    # **bold**
    s = re.sub(r"\*\*([^*\n]+?)\*\*", r"<strong>\1</strong>", s)
    # *italic*（避免和 ** 冲突；只匹配单 * 包裹且内部无 *）
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", s)
    # 页内下潜链接 [文本](#anchor)（v2.3 三层阅读结构：摘要层→详情层）
    s = re.sub(r"\[([^\]\n]+)\]\(#([\w-]+)\)", r'<a class="dive-link" href="#\2">\1</a>', s)
    # 线路箭头美化（贯穿线/认知链等 → 串联全文生效）
    s = re.sub(r"\s→\s", ' <span class="arrow">→</span> ', s)
    # 圈号①-⑳ → 可点段链接（正文任何提到「第①段」处可直接下潜）
    def _cir(m):
        n = ord(m.group(0)) - 0x2460 + 1
        return f'<a class="cir-link" href="#seg{n}">{m.group(0)}</a>'
    s = re.sub(r"[①-⑳]", _cir, s)
    return s

# 段标题与一句话副标题（侧栏与各段顶部用）
SEG_META = {}  # v2.3.4：首场 9 段硬编码已删（render_pack 渲染前整体替换）

# ---------------------------------------------------------------------------
# Markdown 块级解析器（通用）
# ---------------------------------------------------------------------------

SPK_RE = re.compile(r"^\*?-----------------------$")  # placeholder, not used
SPEAKER_LINE_RE = re.compile(
    r"^(?P<lead>>\s*)?\*\*【(?P<sp>[^】]+)】\*\*\s*\[(?P<ts>[\d:]+)\]\s*(?P<rest>.*)$"
)
TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$")
TABLE_SEP_RE = re.compile(r"^\|[\s:|-]+\|\s*$")

def md_to_blocks(md: str):
    """
    把 md 文本切成块列表。每个块是 (kind, payload)。
    kind: 'h1'/'h2'/'h3'/'h4'/'h5'/'hr'/'table'/'ul'/'ol'/'quote_speaker'/'aside'/'quote'/'plain'/'blank'
    """
    lines = md.split("\n")
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.rstrip()

        if stripped == "":
            blocks.append(("blank", ""))
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            blocks.append((f"h{level}", text))
            i += 1
            continue

        # 水平线
        if re.match(r"^-{3,}\s*$", stripped) or re.match(r"^\*{3,}\s*$", stripped):
            blocks.append(("hr", ""))
            i += 1
            continue

        # 说话人行 **【X】** [ts] rest（可能带 > 前缀，原文节选/金句）
        m = SPEAKER_LINE_RE.match(stripped)
        if m:
            blocks.append(("quote_speaker", {
                "speaker": m.group("sp"),
                "ts": m.group("ts"),
                "rest": m.group("rest"),
                "lead": m.group("lead") is not None,
            }))
            i += 1
            continue

        # aside 注释行：> [xxx] ...
        m = re.match(r"^>\s*\[(?P<tag>[^\]]+)\]\s*(?P<rest>.+)$", stripped)
        if m:
            blocks.append(("aside", {"tag": m.group("tag"), "rest": m.group("rest")}))
            i += 1
            continue

        # 块引用（金句以外的普通 > 引用）
        m = re.match(r"^>\s?(?P<rest>.*)$", stripped)
        if m:
            # 合并连续的 > 行
            content_lines = [m.group("rest")]
            j = i + 1
            while j < n:
                m2 = re.match(r"^>\s?(.*)$", lines[j].rstrip())
                if not m2:
                    break
                content_lines.append(m2.group(1))
                j += 1
            blocks.append(("quote", "\n".join(content_lines).strip()))
            i = j
            continue

        # 表格
        if TABLE_ROW_RE.match(stripped):
            table_lines = []
            while i < n and TABLE_ROW_RE.match(lines[i].rstrip()):
                table_lines.append(lines[i].rstrip())
                i += 1
            blocks.append(("table", table_lines))
            continue

        # 无序列表
        if re.match(r"^\s*[-*+]\s+", stripped):
            items = []
            j = i
            while j < n:
                m = re.match(r"^(?P<indent>\s*)[-*+]\s+(?P<text>.*)$", lines[j].rstrip())
                if not m:
                    break
                items.append({"indent": len(m.group("indent")), "text": m.group("text")})
                j += 1
            blocks.append(("ul", items))
            i = j
            continue

        # 有序列表
        if re.match(r"^\s*\d+\.\s+", stripped):
            items = []
            j = i
            while j < n:
                m = re.match(r"^(?P<indent>\s*)(?P<num>\d+)\.\s+(?P<text>.*)$", lines[j].rstrip())
                if not m:
                    break
                items.append({"indent": len(m.group("indent")), "text": m.group("text")})
                j += 1
            blocks.append(("ol", items))
            i = j
            continue

        # 普通段落（合并连续非空非块行）
        para_lines = [stripped]
        j = i + 1
        while j < n:
            nxt = lines[j].rstrip()
            if (nxt == "" or re.match(r"^#{1,6}\s+", nxt) or re.match(r"^[-*+]\s+", nxt)
                    or re.match(r"^\s*\d+\.\s+", nxt) or TABLE_ROW_RE.match(nxt)
                    or re.match(r"^>\s?", nxt) or re.match(r"^-{3,}\s*$", nxt)
                    or SPEAKER_LINE_RE.match(nxt)):
                break
            para_lines.append(nxt)
            j += 1
        blocks.append(("plain", " ".join(para_lines)))
        i = j

    return blocks


# ---------------------------------------------------------------------------
# 块 → HTML 渲染
# ---------------------------------------------------------------------------

def render_table(table_lines, sortable=False):
    rows = []
    for ln in table_lines:
        # 去首尾 |，按 | 切
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return ""
    # 分离 thead / 分隔行 / tbody
    header = rows[0]
    body = []
    for r in rows[1:]:
        if TABLE_SEP_RE.match("|" + "|".join(r) + "|"):
            continue
        body.append(r)
    cls = ' class="data-table sortable"' if sortable else ' class="md-table"'
    out = [f"<table{cls}><thead><tr>"]
    for h in header:
        out.append(f"<th>{inline_fmt(h)}</th>")
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>")
        for c in row:
            out.append(f"<td>{inline_fmt(c)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def render_ul(items):
    # 顶层 li；缩进 > 0 视为嵌套（简单处理：嵌一层）
    out = ["<ul>"]
    for it in items:
        indent = it["indent"]
        cls = ' class="nested"' if indent > 0 else ""
        out.append(f'<li{cls}>{inline_fmt(it["text"])}</li>')
    out.append("</ul>")
    return "".join(out)


def render_ol(items):
    out = ["<ol>"]
    for it in items:
        indent = it["indent"]
        cls = ' class="nested"' if indent > 0 else ""
        out.append(f'<li{cls}>{inline_fmt(it["text"])}</li>')
    out.append("</ol>")
    return "".join(out)


def render_speaker_line(payload, with_ts_link=False, ts_target_prefix="ts"):
    """渲染 **【说话人】** [ts] rest 行。
    with_ts_link=True 时把时间戳做成可点跳转的 <a data-ts>。"""
    sp = payload["speaker"]
    ts = payload["ts"]
    rest = payload["rest"]
    # 段1 金句会把 rest 用引号包起来——去掉首尾配对的弯/直引号
    rest = re.sub(r'^["""\']+', "", rest)
    rest = re.sub(r'["""\']+$', "", rest)
    rest_html = inline_fmt(rest)
    if with_ts_link:
        ts_html = f'<span class="ts" data-ts="{esc(ts)}" title="出处时间戳">[{esc(ts)}] {esc(sp)}</span>'
    else:
        ts_html = f'<span class="ts">[{esc(ts)}] {esc(sp)}</span>'
    return f'<div class="quote">{ts_html} {rest_html}</div>'


def render_blocks_generic(blocks, sortable_tables=False):
    """通用块渲染：把任意 md 块列表转成 HTML 字符串。"""
    out = []
    for kind, payload in blocks:
        if kind == "blank":
            continue
        if kind == "hr":
            out.append('<hr class="soft">')
        elif kind == "h1":
            out.append(f"<h2>{inline_fmt(payload)}</h2>")
        elif kind == "h2":
            out.append(f"<h3>{inline_fmt(payload)}</h3>")
        elif kind == "h3":
            out.append(f"<h4>{inline_fmt(payload)}</h4>")
        elif kind == "h4":
            out.append(f"<h5>{inline_fmt(payload)}</h5>")
        elif kind == "h5":
            out.append(f"<h6>{inline_fmt(payload)}</h6>")
        elif kind == "table":
            out.append(render_table(payload, sortable=sortable_tables))
        elif kind == "ul":
            out.append(render_ul(payload))
        elif kind == "ol":
            out.append(render_ol(payload))
        elif kind == "quote_speaker":
            out.append(render_speaker_line(payload, with_ts_link=False))
        elif kind == "aside":
            tag = payload["tag"]
            rest = payload["rest"]
            out.append(f'<p class="aside"><span class="aside-tag">[{esc(tag)}]</span> {inline_fmt(rest)}</p>')
        elif kind == "quote":
            out.append(f'<blockquote>{inline_fmt(payload)}</blockquote>')
        elif kind == "plain":
            out.append(f"<p>{inline_fmt(payload)}</p>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 9 段解析（按 ## 关键词切块：摘要 / 详细分析 / 金句 / 原文节选）
# ---------------------------------------------------------------------------

def split_seg_sections(md: str):
    """
    返回 dict: {meta, summary, analysis, quotes, raw}.
    通过 ## 关键词识别四块。两种格式都支持：
      - ## 摘要  / ## 详细分析 / ## 金句 / ## 原文节选
      - ## 一、摘要 / ## 二、详细分析 / ## 三、金句 / ## 四、原文节选
    """
    blocks = md_to_blocks(md)

    meta_lines = []
    summary_blocks = []
    analysis_blocks = []
    quotes_blocks = []
    raw_blocks = []

    # 第一块必须是 h1（# 第N段 ...）
    assert blocks and blocks[0][0] == "h1", f"expected h1, got {blocks[0]}"
    title = blocks[0][1]

    current = None
    for kind, payload in blocks[1:]:
        if kind == "h2":
            label = strip_ordinal(payload).strip()
            # 模糊匹配关键词
            if "摘要" in label and "详细" not in label:
                current = "summary"
                continue
            if "详细分析" in label or "分析" in label:
                current = "analysis"
                continue
            if "金句" in label:
                current = "quotes"
                continue
            if "原文节选" in label or "节选" in label:
                current = "raw"
                continue
            # 其他 h2 归到 meta（首部说明）或当前
            if current is None:
                meta_lines.append(("h2", payload))
            else:
                _append_to(current, ("h2", payload), summary_blocks, analysis_blocks, quotes_blocks, raw_blocks)
            continue
        if kind == "h1":
            # 嵌套 h1（不该出现，但容错）
            continue
        if current is None:
            meta_lines.append((kind, payload))
        else:
            _append_to(current, (kind, payload), summary_blocks, analysis_blocks, quotes_blocks, raw_blocks)

    return {
        "title": title,
        "meta": meta_lines,
        "summary": summary_blocks,
        "analysis": analysis_blocks,
        "quotes": quotes_blocks,
        "raw": raw_blocks,
    }


def _append_to(section, item, summary, analysis, quotes, raw):
    if section == "summary":
        summary.append(item)
    elif section == "analysis":
        analysis.append(item)
    elif section == "quotes":
        quotes.append(item)
    elif section == "raw":
        raw.append(item)


def render_analysis_as_cards(blocks):
    """把 analysis 块渲染成卡片堆：按 h3 小节切分，
    每个小节标题 + 其后跟随的段落/列表/表格整体包成一张 .analysis-card。
    第一个 h3 之前的内容（前导，无标题）按通用渲染、不包卡。"""
    groups = []  # each: (title_html_or_None, [blocks])
    cur_title = None
    cur_blocks = []
    seen_h3 = False
    for kind, payload in blocks:
        if kind == "blank":
            continue
        if kind == "h3":
            # 关闭上一组
            if cur_blocks or seen_h3:
                groups.append((cur_title, cur_blocks))
                cur_blocks = []
            cur_title = inline_fmt(payload)
            seen_h3 = True
        else:
            cur_blocks.append((kind, payload))
    # flush 最后一组
    if cur_blocks or cur_title is not None:
        groups.append((cur_title, cur_blocks))

    out = []
    for title, blk in groups:
        body_html = render_blocks_generic(blk)
        if title is None:
            # 前导内容（首个 h3 之前）不包卡
            out.append(body_html)
        else:
            out.append('<div class="analysis-card">')
            out.append(f'<h4 class="ac-title">{title}</h4>')
            out.append(body_html)
            out.append('</div>')
    return "\n".join(out)


def render_seg(seg_num: int, md: str):
    """渲染单段为 HTML（放入 <section id="segN">）。"""
    parts = split_seg_sections(md)
    title = SEG_META.get(seg_num, (parts["title"], ""))[0]
    subtitle = SEG_META.get(seg_num, ("", ""))[1]
    sid = f"seg{seg_num}"
    out = [f'<h2 class="seg-title">{esc(title)}</h2>']
    if subtitle:
        # inline_fmt 而非 esc：副标题里混入的 markdown（**强调**等）正常消化，
        # 不再以字面星号泄漏进页面（2026-08-19 客户丁场缺陷 1）
        out.append(f'<p class="seg-subtitle">{inline_fmt(subtitle)}</p>')

    # meta（时间范围等）
    if parts["meta"]:
        meta_html = render_blocks_generic(parts["meta"])
        # 把 h2 在 meta 里降级为 h4
        meta_html = meta_html.replace("<h3>", "<h4>").replace("</h3>", "</h4>")
        out.append(f'<div class="seg-meta card">{meta_html}</div>')

    # 数金句条数（quote_speaker 行数）
    quotes_count = sum(1 for k, _ in parts["quotes"] if k == "quote_speaker")

    # 段顶粘性小导航（seg-tabs）
    chips = []
    if parts["summary"]:
        chips.append(f'<a class="chip" href="#{sid}-summary">① 摘要</a>')
    if parts["analysis"]:
        chips.append(f'<a class="chip" href="#{sid}-analysis">② 详析</a>')
    if parts["quotes"]:
        chips.append(f'<a class="chip" href="#{sid}-quotes">③ 金句({quotes_count})</a>')
    if parts["raw"]:
        chips.append(f'<a class="chip" href="#{sid}-raw">④ 原文</a>')
    if chips:
        out.append(f'<nav class="seg-tabs" data-seg="{sid}" aria-label="段内导航">')
        out.extend(chips)
        out.append('</nav>')

    # 摘要
    if parts["summary"]:
        out.append(f'<div class="block-summary" id="{sid}-summary">')
        out.append('<h3 class="block-h seg-bh bh-summary"><span class="bh-num">①</span>摘要</h3>')
        out.append(render_blocks_generic(parts["summary"]))
        out.append('</div>')

    # 详细分析（小节做成卡片；v2.3.2 默认折叠——「结论展开、过程折叠」：
    # 段结论已在②层速览可得，点进段的读者多是要金句/原文，详析按需展开。
    # 锚点跳入时由 JS 自动展开，折叠不吃跳转）
    if parts["analysis"]:
        out.append(f'<details class="raw-details" id="{sid}-analysis">')
        out.append('<summary><span class="bh-num">②</span>详析</summary>')
        out.append('<div class="raw-body">')
        out.append(render_analysis_as_cards(parts["analysis"]))
        out.append('</div></details>')

    # 金句
    if parts["quotes"]:
        out.append(f'<div class="block-quotes" id="{sid}-quotes">')
        out.append('<h3 class="block-h seg-bh bh-quotes"><span class="bh-num">③</span>金句 <span class="hint">点击卡片复制</span></h3>')
        # 金句区里的说话人行 → quote 卡，时间戳做成可点跳转
        for kind, payload in parts["quotes"]:
            if kind == "quote_speaker":
                out.append(render_speaker_line(payload, with_ts_link=True))
            elif kind == "blank":
                continue
            elif kind == "hr":
                continue
            else:
                # 其他内容（标题、说明）按通用渲染，但降级
                html_chunk = render_blocks_generic([(kind, payload)])
                # 把金句区里的 h3/h4 降级避免抢风头
                html_chunk = html_chunk.replace("<h3>", "<h5>").replace("</h3>", "</h5>")
                html_chunk = html_chunk.replace("<h4>", "<h5>").replace("</h4>", "</h5>")
                out.append(html_chunk)
        out.append('</div>')

    # 原文节选（默认折叠）
    if parts["raw"]:
        out.append(f'<details class="raw-details seg-raw-details" id="{sid}-raw">')
        out.append('<summary><span class="bh-num">④</span>原文节选</summary>')
        out.append('<div class="raw-body">')
        for kind, payload in parts["raw"]:
            if kind == "quote_speaker":
                # 原文节选里的说话人行 → 紧凑行式
                sp = payload["speaker"]
                ts = payload["ts"]
                rest = payload["rest"]
                rest_html = inline_fmt(rest)
                out.append(
                    f'<p class="line"><span class="sp">{esc(sp)}</span>'
                    f'<span class="ts" data-ts="{esc(ts)}">[{esc(ts)}]</span> '
                    f'<span class="lc">{rest_html}</span></p>'
                )
            elif kind == "blank" or kind == "hr":
                continue
            elif kind == "aside":
                tag = payload["tag"]
                rest = payload["rest"]
                out.append(f'<p class="aside"><span class="aside-tag">[{esc(tag)}]</span> {inline_fmt(rest)}</p>')
            else:
                html_chunk = render_blocks_generic([(kind, payload)])
                # 原文节选里的小节标题（### 段 1 ...）→ h5
                html_chunk = html_chunk.replace("<h3>", "<h5>").replace("</h3>", "</h5>")
                html_chunk = html_chunk.replace("<h4>", "<h5>").replace("</h4>", "</h5>")
                out.append(html_chunk)
        out.append('</div>')
        out.append('</details>')

    return "\n".join(out)


# ---------------------------------------------------------------------------
# 清洗稿（01_清洗稿.md）
# ---------------------------------------------------------------------------

def render_transcript(md: str):
    """渲染清洗稿为 <section id="transcript"> 内的 HTML。"""
    blocks = md_to_blocks(md)
    out = ['<h2 class="seg-title">清洗稿 · 全场逐字</h2>']
    out.append('<p class="seg-subtitle">约 5 小时（00:00:00 – 04:58:40）｜点击任意时间戳可从金句跳回这里</p>')

    # 跳过文件头：找第一个说话人行开始
    start_idx = 0
    for i, (kind, payload) in enumerate(blocks):
        if kind == "quote_speaker":
            start_idx = i
            break

    # 把 ASR 修正对照表单独存（在最后一个 h2 "ASR 修正对照表" 之后）
    asr_start = None
    for i in range(start_idx, len(blocks)):
        kind, payload = blocks[i]
        if kind == "h2" and "ASR" in str(payload):
            asr_start = i
            break

    body_blocks = blocks[start_idx:asr_start] if asr_start else blocks[start_idx:]
    asr_blocks = blocks[asr_start:] if asr_start else []

    out.append('<div class="transcript">')
    line_counter = 0
    for kind, payload in body_blocks:
        if kind == "quote_speaker":
            sp = payload["speaker"]
            ts = payload["ts"]
            rest = payload["rest"]
            rest_html = inline_fmt(rest)
            ts_id = "ts-" + ts.replace(":", "-")
            out.append(
                f'<p class="line" id="{ts_id}" data-ts="{esc(ts)}">'
                f'<span class="sp sp-{sp_color(sp)}">{esc(sp)}</span>'
                f'<span class="ts">[{esc(ts)}]</span> '
                f'<span class="lc">{rest_html}</span></p>'
            )
            line_counter += 1
        elif kind == "aside":
            tag = payload["tag"]
            rest = payload["rest"]
            out.append(f'<p class="aside"><span class="aside-tag">[{esc(tag)}]</span> {inline_fmt(rest)}</p>')
        elif kind == "blank" or kind == "hr":
            continue
        elif kind == "h2":
            out.append(f"<h3>{inline_fmt(payload)}</h3>")
        else:
            # 兜底
            out.append(render_blocks_generic([(kind, payload)]))
    out.append('</div>')

    # ASR 修正对照表（折叠）
    if asr_blocks:
        out.append('<details class="raw-details asr-details">')
        out.append('<summary>展开 ASR 修正对照表</summary>')
        out.append('<div class="raw-body">')
        out.append(render_blocks_generic(asr_blocks, sortable_tables=False))
        out.append('</div>')
        out.append('</details>')

    return "\n".join(out)


def sp_color(speaker: str) -> str:
    """说话人→徽章色类（v2.3.4：首场 4 人硬编码表已删，render_pack 会整体替换此符号）。"""
    return "x"


# ---------------------------------------------------------------------------
# 总览（自写）
# ---------------------------------------------------------------------------

def render_overview():
    """总览区渲染（v2.3.4：首场自写 HTML 已删，render_pack monkey-patch 此符号）。"""
    return ""


# ---------------------------------------------------------------------------
# 方法论清单（03）
# ---------------------------------------------------------------------------

def render_method(md: str):
    blocks = md_to_blocks(md)
    out = ['<h2 class="seg-title">方法论清单</h2>',
           '<p class="seg-subtitle">14 张可复用的思维工具卡 · 定义 + 出处 + 怎么用</p>']
    # 跳过首个 h1
    i = 1
    n = len(blocks)
    card_num = 0
    while i < n:
        kind, payload = blocks[i]
        # 每张卡以 h2 开头（## 1. xxx / ## 9. xxx 等）
        if kind == "h2" and re.match(r"^\d+", payload.strip()):
            card_num += 1
            # 收集这张卡的所有块直到下一个 h2 卡片起始或 hr
            card_blocks = [(kind, payload)]
            j = i + 1
            while j < n:
                k2, p2 = blocks[j]
                if k2 == "h2" and re.match(r"^\d+", str(p2).strip()):
                    break
                if k2 == "hr":
                    break
                card_blocks.append((k2, p2))
                j += 1
            # 渲染卡片
            out.append(render_method_card(card_blocks))
            i = j
            # 跳过卡之间的 hr
            while i < n and blocks[i][0] == "hr":
                i += 1
        elif kind == "h2":
            # 命中校验、补充卡片 等小节标题。
            # 「校验/对照」类=质检数据，默认折叠（v2.3.3 用户反馈：不属于阅读主线）
            j = i + 1
            sec = []
            while j < n and blocks[j][0] != "h2":
                if blocks[j][0] != "blank":
                    sec.append(blocks[j])
                j += 1
            title = payload.strip()
            if "校验" in title or "对照" in title:
                out.append('<details class="raw-details"><summary>'
                           + inline_fmt(title) + ' · 质检数据</summary><div class="raw-body">')
                out.append(render_blocks_generic(sec, sortable_tables=True))
                out.append('</div></details>')
            else:
                out.append(f"<h3>{inline_fmt(title)}</h3>")
                out.append(render_blocks_generic(sec))
            i = j
        elif kind == "blank" or kind == "hr":
            i += 1
        else:
            # 文件头说明、命中校验表等
            out.append(render_blocks_generic([(kind, payload)]))
            i += 1
    return "\n".join(out)


def render_method_card(card_blocks):
    # 第一块是 h2 标题
    title = card_blocks[0][1]
    m = re.match(r"^(?P<num>\d+)\.\s*(?P<name>.+)$", title.strip())
    if m:
        num = m.group("num")
        name = m.group("name")
        header = f'<div class="card-num">卡 {num}</div><div class="card-name">{inline_fmt(name)}</div>'
    else:
        header = f'<div class="card-name">{inline_fmt(title)}</div>'
    body = []
    for kind, payload in card_blocks[1:]:
        if kind == "blank":
            continue
        if kind == "ul":
            # 每张卡的 - 定义/出处/怎么用用
            for it in payload:
                body.append(f'<div class="mfield">{inline_fmt(it["text"])}</div>')
        else:
            body.append(render_blocks_generic([(kind, payload)]))
    return f'<div class="card method-card"><div class="card-head">{header}</div><div class="card-body">{"".join(body)}</div></div>'


# ---------------------------------------------------------------------------
# 术语表（04）
# ---------------------------------------------------------------------------

def render_glossary(md: str):
    blocks = md_to_blocks(md)
    out = ['<h2 class="seg-title">术语表</h2>',
           '<p class="seg-subtitle">32 条 · 一句话解释 + 出处段号</p>']
    i = 1
    n = len(blocks)
    while i < n:
        kind, payload = blocks[i]
        if kind == "h3":
            # 每条术语以 ### 起头
            term = payload.strip()
            j = i + 1
            desc_lines = []
            src_line = None
            while j < n:
                k2, p2 = blocks[j]
                if k2 == "h3":
                    break
                if k2 == "plain" and isinstance(p2, str) and p2.startswith("出处"):
                    src_line = p2
                elif k2 == "plain":
                    desc_lines.append(p2)
                elif k2 == "blank":
                    pass
                else:
                    desc_lines.append(f"[{k2}] {p2}")
                j += 1
            desc = " ".join(desc_lines).strip()
            src_html = f'<div class="glossary-src">{inline_fmt(src_line)}</div>' if src_line else ""
            out.append(
                f'<div class="card glossary-card">'
                f'<div class="glossary-term">{inline_fmt(term)}</div>'
                f'<div class="glossary-desc">{inline_fmt(desc)}</div>'
                f'{src_html}'
                f'</div>'
            )
            i = j
        elif kind == "blank" or kind == "hr":
            i += 1
        elif kind == "h2":
            out.append(f"<h3>{inline_fmt(payload)}</h3>")
            i += 1
        else:
            out.append(render_blocks_generic([(kind, payload)]))
            i += 1
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 人物角色卡（05）—— 特殊渲染
# ---------------------------------------------------------------------------

PEOPLE_COLOR = {}  # v2.3.4：首场 4 人硬编码已删（render_pack 用 PALETTE 轮询）
PEOPLE_RATIO = {}  # v2.3.4：同上，render_pack.extract_people 自动提取
PEOPLE_TAGLINE = {}
PEOPLE_ROLE = {}
PEOPLE_STANCE = {}


def render_people(md: str):
    """人物卡渲染（v2.3.4：首场硬编码已删，render_pack monkey-patch 此符号）。"""
    return ""


# ---------------------------------------------------------------------------
# 关键数据（06）—— 表格 + mini 条
# ---------------------------------------------------------------------------

def render_data(md: str):
    """数据速查渲染（v2.3.4：首场 databars 硬编码已删，render_pack monkey-patch 此符号）。"""
    return ""


# ---------------------------------------------------------------------------
# 议题关联地图（07）—— 三层流式信息图
# ---------------------------------------------------------------------------

def render_map(md: str):
    """议题地图渲染（v2.3.4：首场图形化硬编码已删，render_pack monkey-patch 此符号；ASCII 图走 render_pack.render_md_with_code）。"""
    return ""


# ---------------------------------------------------------------------------
# 洞察卡片（08）
# ---------------------------------------------------------------------------

# 字段头：**核心**： / **证据**： / **启示**： / **反方（本场张力）**： / **边界**：
INSIGHT_FIELD_RE = re.compile(r"^\*\*(?P<label>[^*：:]+)\*\*[：:]\s*(?P<rest>.*)$")


def _insight_field_key(label: str):
    if "核心" in label:
        return "core"
    if "证据" in label:
        return "evidence"
    if "启示" in label:
        return "lesson"
    if "反方" in label or "边界" in label or "张力" in label:
        return "counter"
    return None


def render_insight_card(num, name, card_md):
    """渲染单张洞察卡：标题 + 核心突出 + 证据引用块 + 启示 + 反方/边界。"""
    blocks = md_to_blocks(card_md)
    header = (f'<div class="card-num">卡 {esc(num)}</div>'
              f'<div class="card-name">{inline_fmt(name)}</div>')
    body = []
    for kind, payload in blocks:
        if kind == "blank" or kind == "hr":
            continue
        if kind == "plain":
            m = INSIGHT_FIELD_RE.match(payload.strip())
            if m:
                key = _insight_field_key(m.group("label"))
                if key:
                    label = m.group("label").strip()
                    rest = m.group("rest").strip()
                    tag = f'<span class="ifield-tag">{inline_fmt(label)}</span>'
                    if key == "core":
                        body.append(f'<div class="ifield icore">{tag}{inline_fmt(rest)}</div>')
                    elif key == "counter":
                        body.append(f'<div class="ifield icounter">{tag}{inline_fmt(rest)}</div>')
                    elif key == "evidence":
                        # 证据字段头本身；后续 quote_speaker 行才是证据
                        if rest:
                            body.append(f'<div class="ifield">{tag}{inline_fmt(rest)}</div>')
                    else:  # lesson
                        body.append(f'<div class="ifield">{tag}{inline_fmt(rest)}</div>')
                    continue
            body.append(f'<p>{inline_fmt(payload)}</p>')
        elif kind == "quote_speaker":
            # 证据原话 → .quote 卡，时间戳可点跳 #transcript（与金句一致）
            body.append(render_speaker_line(payload, with_ts_link=True))
        elif kind == "quote":
            # 非说话人格式的证据（如时间戳区间）→ 引用块兜底
            body.append(f'<blockquote class="insight-evidence">{inline_fmt(payload)}</blockquote>')
        else:
            body.append(render_blocks_generic([(kind, payload)]))
    return (f'<div class="card method-card insight-card" id="insight-{esc(num)}">'
            f'<div class="card-head">{header}</div>'
            f'<div class="card-body">{"".join(body)}</div>'
            f'</div>')


def render_insight_map():
    """洞察地图图形化渲染（v2.3.4：首场硬编码已删，死路径）。"""
    return ""


def render_insights(md: str):
    """洞察卡区渲染（v2.3.4：首场实现已删，render_pack monkey-patch 此符号）。"""
    return ""


# ---------------------------------------------------------------------------
# 模板 + 主入口
# ---------------------------------------------------------------------------

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>聊聊AI工业应用 · 全场整理</title>
<style>
:root{
  --bg:#f7f8fa;--surface:#fff;--text:#1f2329;--muted:#646a73;--border:#ebedf0;
  /* accent/tag 换深一档提对比度（2026-08-19 缺陷 5：旧 #3370ff 白底 4.3:1、#e8910a 2.5:1） */
  --accent:#2b62d6;--accent-soft:#dee6fb;--accent-strong:#1e4fae;
  --tag-blue:#2b62d6;--tag-orange:#9a5f00;--tag-red:#e5404e;--tag-purple:#8a5cf6;
  --shadow:0 1px 3px rgba(0,0,0,.05),0 1px 2px rgba(0,0,0,.03);
  --shadow-hover:0 4px 12px rgba(0,0,0,.08);
  --radius:8px;--radius-lg:12px;
  --topbar-h:49px;
  --seg-tabs-h:44px;
  --sticky-offset:calc(var(--topbar-h) + var(--seg-tabs-h) + 12px);
}
[data-theme="dark"]{
  --bg:#161616;--surface:#222;--text:#e6e6e6;--muted:#999;--border:#333;
  --accent:#5b8bff;--accent-soft:#1e2a44;--accent-strong:#7da3ff;
  --shadow:0 1px 3px rgba(0,0,0,.4);--shadow-hover:0 4px 12px rgba(0,0,0,.5);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:system-ui,-apple-system,"PingFang SC","Helvetica Neue",sans-serif;
  background:var(--bg);color:var(--text);line-height:1.75;font-size:15px;
  -webkit-font-smoothing:antialiased;
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* 布局 */
.layout{display:flex;min-height:100vh}
.sidebar{
  width:240px;position:fixed;top:0;left:0;bottom:0;
  background:var(--surface);border-right:1px solid var(--border);
  padding:18px 14px;overflow-y:auto;z-index:50;
}
.sidebar-brand{
  font-size:14px;color:var(--accent);font-weight:700;margin:0 6px 6px;
  padding:8px 10px;border-radius:6px;background:var(--accent-soft);
}
.sidebar-brand small{display:block;font-weight:400;color:var(--muted);font-size:11px;margin-top:2px}
.sidebar nav{margin-top:10px}
.sidebar a{
  display:block;color:var(--muted);text-decoration:none;
  padding:7px 12px;border-radius:6px;font-size:13px;margin:1px 0;
}
.sidebar a:hover{background:var(--bg);text-decoration:none;color:var(--text)}
.sidebar a.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.sidebar .nav-group{padding-left:10px;font-size:12px;margin-top:2px}
.sidebar .nav-group .nav-group-title{
  font-size:11px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.06em;padding:8px 12px 4px;font-weight:600;
}

main{
  margin-left:240px;max-width:920px;padding:24px 40px 80px;width:100%;
}
section{margin-bottom:56px;scroll-margin-top:24px}

/* topbar */
.topbar{
  position:sticky;top:0;background:var(--bg);
  display:flex;gap:8px;align-items:center;
  padding:10px 0 14px;margin-bottom:8px;z-index:20;
  border-bottom:1px solid var(--border);
}
.topbar-group{display:flex;gap:6px;align-items:center;flex-shrink:0}
.topbar-search{display:flex;gap:6px;align-items:center;flex:1;min-width:0}
.topbar-search input{
  flex:1;min-width:60px;padding:9px 14px;border:1px solid var(--border);border-radius:8px;
  background:var(--surface);color:var(--text);font-size:14px;outline:none;
  transition:border-color .15s,box-shadow .15s;
}
.topbar-search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.topbar .count{font-size:12px;color:var(--muted);white-space:nowrap;font-family:ui-monospace,monospace}
.topbar .count.empty{color:var(--muted)}
.topbar .count.none{color:var(--muted);opacity:.6}
button.icon{
  background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:8px 12px;cursor:pointer;color:var(--text);font-size:14px;
  transition:background .15s,border-color .15s,opacity .15s;
  flex-shrink:0;
}
button.icon:hover{background:var(--bg);border-color:var(--accent)}
button.icon:disabled{opacity:.4;cursor:not-allowed}
button.icon:disabled:hover{background:var(--surface);border-color:var(--border)}
button.icon.search-nav-btn{padding:8px 10px;line-height:1}
button.icon.font-btn{padding:8px 10px;font-size:13px;font-weight:600}
.hamburger{display:none}
.sidebar-toggle{display:inline-block}

/* 阅读进度条 */
.reading-progress{
  position:fixed;top:0;left:0;height:3px;width:0;
  background:var(--accent);z-index:100;
  transition:width .08s linear;
  pointer-events:none;
}

/* 回到顶部 */
.back-to-top{
  position:fixed;right:22px;bottom:22px;
  width:42px;height:42px;border-radius:50%;
  padding:0;font-size:18px;line-height:1;
  display:flex;align-items:center;justify-content:center;
  opacity:0;visibility:hidden;transform:translateY(8px);
  transition:opacity .2s,visibility .2s,transform .2s,background .15s,border-color .15s;
  z-index:90;box-shadow:var(--shadow-hover);
}
.back-to-top.show{opacity:1;visibility:visible;transform:translateY(0)}
.back-to-top:hover{background:var(--accent);color:#fff;border-color:var(--accent)}

/* 折叠后的展开按钮（左上角浮动，仅折叠态可见） */
.sidebar-reopen{
  position:fixed;left:14px;top:64px;
  width:34px;height:34px;border-radius:8px;
  padding:0;font-size:18px;line-height:1;
  display:none;align-items:center;justify-content:center;
  z-index:55;box-shadow:var(--shadow);
}
body.sidebar-collapsed .sidebar-reopen{display:flex}

/* 侧栏折叠态（桌面） */
body.sidebar-collapsed .sidebar{transform:translateX(-100%)}
body.sidebar-collapsed main{margin-left:0}
.sidebar{transition:transform .22s ease}
main{transition:margin-left .22s ease}

/* 搜索当前命中：深色高亮，区别于其它命中 */
mark.srch{background:#ffe58f;color:inherit;padding:0 2px;border-radius:2px}
[data-theme="dark"] mark.srch{background:#806b1f;color:#fff}
mark.srch.cur{background:#ff9c30;color:#fff}
[data-theme="dark"] mark.srch.cur{background:#ff9c30;color:#1f2329}
mark.jumpto{background:#ff9c30;color:#fff;animation:轻量模型2.4s ease-out}

/* 标题 */
h2.seg-title{
  font-size:24px;margin:0 0 4px;font-weight:700;letter-spacing:-.01em;
  border-bottom:2px solid var(--accent);padding-bottom:8px;
}
.seg-subtitle{color:var(--muted);font-size:13px;margin:0 0 20px}
h3{font-size:18px;margin:28px 0 10px;font-weight:600}
h4{font-size:15px;margin:22px 0 8px;font-weight:600;color:var(--text)}
h5{font-size:13px;margin:14px 0 6px;font-weight:600;color:var(--muted)}
.block-h{
  font-size:14px;color:var(--accent);font-weight:700;
  text-transform:uppercase;letter-spacing:.06em;margin:24px 0 12px;
  padding-bottom:4px;border-bottom:1px dashed var(--border);
}
.hint{font-size:12px;color:var(--muted);font-weight:400}

/* 段顶粘性小导航 seg-tabs */
.seg-tabs{
  position:sticky;top:var(--topbar-h);z-index:15;
  display:flex;gap:8px;align-items:center;
  padding:8px 0;margin:0 0 16px;
  background:rgba(247,248,250,.82);
  backdrop-filter:blur(10px) saturate(1.2);
  -webkit-backdrop-filter:blur(10px) saturate(1.2);
  border-bottom:1px solid var(--border);
  overflow-x:auto;scrollbar-width:thin;
}
[data-theme="dark"] .seg-tabs{background:rgba(22,22,22,.82)}
.seg-tabs::-webkit-scrollbar{height:4px}
.seg-tabs::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.seg-tabs .chip{
  flex-shrink:0;display:inline-flex;align-items:center;gap:3px;
  padding:5px 13px;border-radius:16px;
  background:var(--surface);border:1px solid var(--border);
  color:var(--muted);font-size:13px;font-weight:600;
  text-decoration:none;cursor:pointer;white-space:nowrap;
  transition:background .15s,border-color .15s,color .15s;
}
.seg-tabs .chip:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.seg-tabs .chip.active{background:var(--accent);border-color:var(--accent);color:#fff}

/* 四块编号彩条标题 seg-bh */
.block-summary,.block-analysis,.block-quotes,details.raw-details{
  scroll-margin-top:var(--sticky-offset);
}
.block-h.seg-bh{
  display:inline-flex;align-items:center;gap:8px;
  border-bottom:none;text-transform:none;letter-spacing:0;
  padding:6px 14px 6px 10px;margin:22px 0 14px;
  border-radius:0 8px 8px 0;border-left:4px solid var(--accent);
  background:var(--accent-soft);color:var(--accent);
  font-size:14px;font-weight:700;
}
.block-h .bh-num{font-size:15px;font-weight:700;line-height:1;opacity:.85}
.block-h .hint{color:inherit;opacity:.6;font-weight:400}
.block-h.bh-summary{border-left-color:var(--accent);background:var(--accent-soft);color:var(--accent)}
.block-h.bh-analysis{border-left-color:var(--text);background:var(--bg);color:var(--text)}
.block-h.bh-quotes{
  border-left-color:#9a5f00;background:#9a5f001a;color:#9a5f00;
}
[data-theme="dark"] .block-h.bh-quotes{color:#f0a830}
.block-h.bh-raw{border-left-color:var(--muted);background:var(--bg);color:var(--muted)}
/* 原文 details 折叠头：与 ④ 编号体系一致（muted 左竖条） */
details.seg-raw-details>summary{
  display:flex;align-items:center;gap:8px;
  border-left:4px solid var(--muted);color:var(--muted);
  font-size:14px;font-weight:700;padding-left:14px;
}
details.seg-raw-details>summary .bh-num{font-size:15px;opacity:.85}

/* 详析卡片 analysis-card */
.analysis-card{
  border:1px solid var(--border);border-radius:var(--radius);
  padding:14px 18px;margin:12px 0;background:var(--surface);
  transition:box-shadow .15s,border-color .15s;
}
.analysis-card:hover{box-shadow:var(--shadow-hover);border-color:var(--accent)}
.analysis-card .ac-title{
  margin:0 0 10px;font-size:15.5px;font-weight:700;color:var(--accent);
  padding-bottom:6px;border-bottom:1px dashed var(--border);line-height:1.4;
}
.analysis-card > p:first-child,
.analysis-card > ul:first-child,
.analysis-card > ol:first-child,
.analysis-card > table:first-child,
.analysis-card > blockquote:first-child{margin-top:0}
.analysis-card > *:last-child{margin-bottom:0}

/* 金句高亮色带 block-quotes */
.block-quotes{
  background:var(--accent-soft);border-radius:var(--radius-lg);
  padding:14px 18px 18px;margin:18px 0;
  border-left:4px solid #9a5f00;
}
.block-quotes .block-h{margin-top:0}
.block-quotes .quote{background:var(--surface)}
[data-theme="dark"] .block-quotes .quote{background:#1a1a1a}

/* 卡片 */
.card{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:16px 18px;margin:12px 0;box-shadow:var(--shadow);
}
.overview-card{padding:18px 20px}
.overview-card h3{margin-top:0}
.seg-meta{background:var(--accent-soft);border-color:transparent;font-size:13px;color:var(--muted)}
.seg-meta p{margin:4px 0}

/* 块级 */
p{margin:8px 0}
ul,ol{margin:8px 0;padding-left:22px}
li{margin:3px 0}
ul.nested,ol.nested{padding-left:18px;margin:4px 0}
strong{font-weight:600;color:var(--text)}
hr.soft{border:none;border-top:1px dashed var(--border);margin:24px 0}
blockquote{
  border-left:3px solid var(--accent);background:var(--accent-soft);
  padding:10px 14px;border-radius:0 6px 6px 0;margin:12px 0;font-size:14px;color:var(--text);
}
.mono{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  background:var(--bg);padding:1px 6px;border-radius:4px;font-size:.88em;
  border:1px solid var(--border);
}
[data-theme="dark"] .mono{background:#1a1a1a}

/* 金句 quote 卡 */
.quote{
  position:relative;cursor:pointer;
  border-left:3px solid var(--accent);background:var(--accent-soft);
  padding:12px 16px;border-radius:0 8px 8px 0;margin:10px 0;
  font-size:14px;line-height:1.75;color:var(--text);
  transition:transform .12s,box-shadow .15s;
}
.quote:hover{transform:translateX(2px);box-shadow:var(--shadow-hover)}
.quote:active{transform:translateX(2px) scale(.997)}
.quote .ts{
  display:inline-block;font-family:ui-monospace,monospace;font-size:12px;
  background:var(--accent);color:#fff;padding:2px 8px;border-radius:10px;
  margin-right:8px;font-weight:600;vertical-align:middle;
}
.quote a.ts:hover{text-decoration:none;opacity:.9}
.quote::after{
  content:"复制";position:absolute;right:12px;top:12px;
  font-size:11px;color:var(--muted);opacity:0;transition:opacity .15s;
}
.quote:hover::after{opacity:.7}
.quote.copied::after{content:"已复制 ✓";opacity:1;color:#2da94f}

/* 原文节选折叠 */
details.raw-details{
  margin:18px 0;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:0;overflow:hidden;
}
details.raw-details>summary{
  cursor:pointer;padding:14px 18px;background:var(--bg);
  font-weight:600;font-size:13px;color:var(--accent);
  list-style:none;user-select:none;
  border-bottom:1px solid transparent;
}
details.raw-details[open]>summary{border-bottom-color:var(--border)}
details.raw-details>summary::-webkit-details-marker{display:none}
details.raw-details>summary::before{
  content:"▶ ";font-size:10px;margin-right:6px;transition:transform .15s;display:inline-block;
}
details.raw-details[open]>summary::before{transform:rotate(90deg)}
details.raw-details .raw-body{padding:14px 18px}

/* 清洗稿/原文节选说话人行 —— .line 行式（.transcript 与 .raw-body 两容器共用，
   2026-08-19 缺陷 3 修复）。作用域必须带 .line 前缀：裸 .raw-body .ts 会以同特异性
   覆盖金句卡 .quote .ts 的白字（蓝底灰字回归，2026-09-04 用户实测发现） */
.line{
  margin:6px 0;padding:8px 12px;border-radius:6px;
  border-left:2px solid transparent;font-size:14px;
  transition:background .15s,box-shadow .15s;
}
.line:hover{background:var(--bg)}
.line.轻量模型{
  background:#fff3a0;box-shadow:0 0 0 3px #ffe58f;
  animation:轻量模型2.4s ease-out;
}
[data-theme="dark"] .line.轻量模型{background:#5a4e1a;box-shadow:0 0 0 3px #806b1f}
@keyframes轻量模型{0%{background:#ffe58f}100%{background:transparent}}
.line .sp{
  display:inline-block;font-weight:700;font-size:12px;
  padding:1px 8px;border-radius:4px;margin-right:6px;vertical-align:middle;
  min-width:48px;text-align:center;
}
/* 人名徽章色：旧 #3370ff/#e8910a 对白底仅 2.5-4.3:1，换深一档（2026-08-19 缺陷 5） */
.line .sp-h{background:#2b62d6;color:#fff}
.line .sp-g{background:#9a5f00;color:#fff}
.line .sp-l{background:#8a5cf6;color:#fff}
.line .sp-z{background:#e5404e;color:#fff}
.line .sp-x{background:var(--muted);color:#fff}
.line .ts{
  display:inline-block;font-family:ui-monospace,monospace;font-size:11px;
  color:var(--muted);margin-right:8px;vertical-align:middle;
}
.line .lc{color:var(--text)}

/* aside 注释 */
p.aside{
  font-size:12px;color:var(--muted);margin:2px 0 2px 14px;
  padding:4px 10px;background:var(--bg);border-radius:4px;
  border-left:2px solid var(--border);
}
.aside-tag{font-family:ui-monospace,monospace;color:var(--accent);font-weight:600}

/* 表格 */
.md-table,.data-table{
  border-collapse:collapse;width:100%;font-size:13px;margin:14px 0;
  background:var(--surface);border:1px solid var(--border);border-radius:8px;
  overflow:hidden;
}
.md-table th,.data-table th,.md-table td,.data-table td{
  padding:9px 12px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top;
}
.md-table th,.data-table th{
  background:var(--bg);font-weight:600;color:var(--text);font-size:12px;
}
.md-table tr:last-child td,.data-table tr:last-child td{border-bottom:none}
.data-table.sortable th{cursor:pointer;user-select:none;position:relative}
.data-table.sortable th:hover{background:var(--accent-soft);color:var(--accent)}
.data-table.sortable th::after{
  content:" ⇅";font-size:10px;color:var(--muted);font-weight:400;
}
.data-table.sortable th.sort-asc::after{content:" ↑";color:var(--accent)}
.data-table.sortable th.sort-desc::after{content:" ↓";color:var(--accent)}

/* 方法论卡 */
.method-card{padding:0;overflow:hidden}
.method-card .card-head{
  display:flex;align-items:center;gap:12px;
  padding:12px 16px;background:var(--accent-soft);
  border-bottom:1px solid var(--border);
}
.method-card .card-num{
  font-family:ui-monospace,monospace;font-size:11px;font-weight:700;
  background:var(--accent);color:#fff;padding:3px 10px;border-radius:10px;
}
.method-card .card-name{font-weight:700;font-size:15px;color:var(--text)}
.method-card .card-body{padding:12px 16px}
.method-card .mfield{font-size:13px;margin:6px 0;padding-left:0}
.method-card .mfield strong{color:var(--accent)}

/* 洞察卡片 */
.insight-card .ifield{font-size:13px;margin:8px 0;line-height:1.75}
.insight-card .ifield-tag{
  display:inline-block;font-family:ui-monospace,monospace;font-size:11px;
  font-weight:700;color:var(--accent);background:var(--accent-soft);
  padding:1px 8px;border-radius:4px;margin-right:6px;vertical-align:middle;
}
.insight-card .icore{font-size:15.5px;font-weight:600;margin:12px 0;padding:10px 12px;background:var(--accent-soft);border-left:3px solid var(--accent);border-radius:0 6px 6px 0;line-height:1.7}
.insight-dim{font-size:13px;font-weight:700;color:var(--accent);letter-spacing:.04em;margin:26px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--accent-soft)}
.insight-card .icore .ifield-tag{background:var(--accent);color:#fff}
.insight-card .icounter{
  border-left:2px solid #e5404e;background:#e5404e0d;
  padding:8px 12px;border-radius:0 6px 6px 0;margin:10px 0;font-size:13px;
}
.insight-card .icounter .ifield-tag{color:#e5404e;background:#e5404e1a}
[data-theme="dark"] .insight-card .icounter{background:#3a141680}
.insight-card .quote{margin:6px 0;font-size:13px}
.insight-card blockquote.insight-evidence{font-size:13px;margin:6px 0}
/* ASCII 洞察地图 */
pre.ascii-map{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12px;line-height:1.5;
  background:var(--bg);color:var(--text);
  border:1px solid var(--border);border-radius:8px;
  padding:14px 16px;margin:14px 0;
  overflow-x:auto;white-space:pre;
}
[data-theme="dark"] pre.ascii-map{background:#1a1a1a}

/* 洞察卡锚点偏移（洞察地图图形化样式已随首场渲染函数废弃删除，2026-08-19 缺陷 4） */
.insight-card{scroll-margin-top:100px}

/* 术语表 */
.glossary-card{padding:12px 16px}
.glossary-term{
  font-weight:700;font-size:15px;color:var(--accent);
  font-family:ui-monospace,monospace;margin-bottom:4px;
}
.glossary-desc{font-size:13px;color:var(--text);line-height:1.7}
.glossary-src{font-size:11px;color:var(--muted);margin-top:4px;font-family:ui-monospace,monospace}

/* 人物卡网格 */
.people-grid{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:14px;margin:16px 0;
}
.people-card{padding:16px}
.people-head{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.avatar{
  width:48px;height:48px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  color:#fff;font-weight:700;font-size:18px;flex-shrink:0;
}
.people-name{font-weight:700;font-size:16px}
.people-role{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;margin-top:3px}
.people-line{font-size:13px;color:var(--text);margin:8px 0;line-height:1.6}
.people-stance{font-size:12px;margin:6px 0 2px;color:var(--text)}
.people-stance .stance-label{display:inline-block;font-size:10px;font-weight:700;color:var(--muted);background:var(--bg);border:1px solid var(--border);padding:1px 6px;border-radius:4px;margin-right:6px;letter-spacing:.04em;vertical-align:middle}
.people-bar-wrap{margin-top:8px}
.people-bar-label{font-size:11px;color:var(--muted);margin-bottom:4px}
.people-bar-track{height:6px;background:var(--bg);border-radius:3px;overflow:hidden}
.people-bar{height:100%;border-radius:3px}

.people-detail{margin-top:16px}
.people-detail-card{margin:14px 0;padding:14px 18px}
.people-detail-name{margin:0 0 8px;font-size:17px}
.people-quote{font-size:13px}

/* 高亮（mark.srch / mark.srch.cur 规则在 topbar 区域）
   注：databars / map-fig / map-layer / chip 通用块已删——首场图形化渲染函数
   （render_data/render_map/render_insight_map）被 render_pack monkey-patch 取代，
   正文只出 pre.ascii-map 与可排序表格；通用 .chip 删除同时解除移动端
   .chip{width:100%} 对 seg-tabs 胶囊的误伤（2026-08-19 缺陷 4） */

/* 总览 toc */
.seg-toc{padding-left:22px;font-size:14px;line-height:2}
.seg-toc a{color:var(--text)}
.seg-toc a:hover{color:var(--accent)}
.people-quick{padding-left:18px;font-size:14px;line-height:2}

/* v2.3 三层阅读结构：阅读协议横幅 + 简报/总结层 + 下潜链接 */
.read-protocol{
  display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;
  padding:10px 16px;margin:0 0 16px;border-radius:var(--radius);
  background:var(--accent-soft);border-left:4px solid var(--accent);
  font-size:12.5px;color:var(--text);
}
.read-protocol b{color:var(--accent)}
.dive-link{
  color:var(--accent);text-decoration:none;border-bottom:1px dashed var(--accent);
  padding:0 1px;
}
.dive-link:hover{border-bottom-style:solid}
.digest-list{list-style:none;padding:0;margin:0}
.digest-list li{
  padding:7px 0;border-bottom:1px dashed var(--border);
  font-size:13.5px;line-height:1.65;
}
.digest-list li:last-child{border-bottom:none}
.digest-list .dl-title{font-weight:600}
.digest-insights{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.digest-insights a{
  font-size:12.5px;padding:4px 10px;border-radius:14px;
  border:1px solid var(--border);background:var(--surface);
}
.digest-insights a:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}

/* v2.3.8 三层阅读 v2：①执行摘要卡（醒目可折叠，全 BLUF）+ ②分段速览行卡 */
.brief-card{
  border:1px solid color-mix(in srgb,var(--accent) 35%,var(--border));
  border-left:5px solid var(--accent);
  border-radius:var(--radius-lg);
  background:linear-gradient(180deg,var(--accent-soft),var(--surface) 170px);
  box-shadow:var(--shadow);
}
.brief-card>summary{
  display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
  padding:14px 18px;cursor:pointer;list-style:none;user-select:none;
}
.brief-card>summary::-webkit-details-marker{display:none}
.brief-card>summary::before{
  content:"▶ ";font-size:10px;margin-right:2px;display:inline-block;
  transition:transform .15s;color:var(--accent);
}
.brief-card[open]>summary::before{transform:rotate(90deg)}
.brief-card .bc-num{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:24px;height:24px;border-radius:50%;flex-shrink:0;
  background:var(--accent);color:#fff;font-size:13px;font-weight:700;
  transform:translateY(3px);
}
.brief-card .bc-title{font-size:18px;font-weight:700;color:var(--accent-strong)}
.brief-card .bc-hint{font-size:12px;color:var(--muted)}
.brief-card-body{padding:2px 18px 14px}
.brief-card-body .bc-sec{margin:10px 0}
.brief-card-body .bc-sec>p:first-child{margin-top:0}
.brief-card-body table{font-size:12.5px;margin:8px 0}  /* 待办表精简 */
.brief-card-body th,.brief-card-body td{padding:6px 10px}
.brief-card-body .bc-risk>p{font-size:13px}
.brief-foot{
  display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  padding:10px 2px 2px;margin-top:10px;border-top:1px dashed var(--border);
  font-size:13px;
}
.brief-foot .bf-skip{font-weight:600}
.brief-foot .bf-sep{color:var(--muted)}
.seg-quick{list-style:none;padding:0;margin:0}
.sq-row{
  display:flex;gap:12px;align-items:flex-start;
  padding:10px 2px;border-bottom:1px dashed var(--border);
}
.sq-row:last-child{border-bottom:none}
.sq-num{
  flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;
  width:26px;height:26px;border-radius:50%;margin-top:2px;
  background:var(--accent);color:#fff;font-size:13px;font-weight:700;
  text-decoration:none;
}
.sq-num:hover{opacity:.85;text-decoration:none}
.sq-body{flex:1;min-width:0}
.sq-title{font-weight:600;font-size:14px;color:var(--text);text-decoration:none;line-height:1.5}
.sq-title:hover{color:var(--accent)}
.sq-sum{margin:2px 0 0;font-size:13px;color:var(--muted);line-height:1.65}
.sq-open{
  flex-shrink:0;margin-top:2px;white-space:nowrap;
  font-size:12px;color:var(--accent);text-decoration:none;
  border:1px solid var(--border);border-radius:14px;padding:3px 10px;
}
.sq-open:hover{border-color:var(--accent)}
@media print{.sq-row{break-inside:avoid;page-break-inside:avoid}}

/* v2.3.3 图形化地图：层带 / 节点流 / 线路箭头 / 终端风回退 */
.arrow{color:var(--accent);font-weight:700;padding:0 1px}
.gl-layer{
  border:1px solid var(--border);border-left:5px solid var(--c);
  background:color-mix(in srgb,var(--c) 7%,var(--surface));
  border-radius:8px;padding:12px 16px;margin:10px 0;
}
.gl-layer-h{display:flex;align-items:baseline;gap:10px;margin-bottom:8px}
.gl-layer-name{font-weight:700;font-size:14px;color:var(--c)}
.gl-layer-tag{font-size:11.5px;color:var(--muted)}
.gl-chips{display:flex;flex-wrap:wrap;gap:8px}
.gl-chip{
  display:inline-flex;align-items:center;gap:6px;text-decoration:none;
  color:var(--text);background:var(--surface);
  border:1px solid color-mix(in srgb,var(--c) 40%,var(--border));
  border-radius:16px;padding:5px 12px;font-size:12.5px;
  transition:transform .12s,box-shadow .12s;
}
a.gl-chip:hover{transform:translateY(-1px);box-shadow:0 2px 8px rgba(0,0,0,.14);text-decoration:none}
.gl-chip .gl-num{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:20px;height:20px;border-radius:50%;
  background:var(--c);color:#fff;font-size:11px;font-weight:700;
}
.gl-flow{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:8px 0 14px}
.gl-flow-name{
  font-size:12px;font-weight:700;color:#fff;background:var(--c);
  border-radius:12px;padding:3px 10px;flex-shrink:0;
}
.gl-node{
  display:inline-flex;align-items:center;text-decoration:none;
  background:color-mix(in srgb,var(--c,#3b82f6) 10%,var(--surface));
  border:1px solid color-mix(in srgb,var(--c,#3b82f6) 40%,var(--border));
  color:var(--text);border-radius:10px;padding:4px 10px;font-size:12.5px;
}
a.gl-node:hover{box-shadow:0 2px 8px rgba(0,0,0,.14);text-decoration:none}
.gl-chip-num{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:18px;height:18px;border-radius:50%;
  color:#fff;font-size:10.5px;font-weight:700;flex-shrink:0;
}
.cir-link{
  color:var(--accent);text-decoration:none;
  border-bottom:1px dotted var(--accent);padding:0 1px;
}
.cir-link:hover{border-bottom-style:solid}
.gl-arr{color:var(--c,#3b82f6);font-weight:800;padding:0 2px}
.gl-note{font-size:12px;color:var(--muted);margin:6px 0}
pre.ascii-map{
  background:#101418;color:#d6e2f0;border:1px solid #2a3442;
  border-left:4px solid #3b82f6;
}
pre.ascii-map::before{
  content:"◈ 结构图";display:block;color:#7ee0a3;font-size:11px;
  font-weight:700;margin-bottom:6px;letter-spacing:.05em;
}
[data-theme="dark"] pre.ascii-map{background:#0d1117}

/* 响应式 */
@media(max-width:820px){
  .sidebar{
    position:fixed;top:0;left:0;right:0;bottom:auto;
    width:auto;display:none;padding:14px;
    box-shadow:0 4px 16px rgba(0,0,0,.18);
  }
  .sidebar.open{display:block}
  body.sidebar-collapsed .sidebar{transform:none}
  main{margin-left:0;padding:16px 16px 60px}
  .hamburger{display:inline-block}
  /* 窄屏：侧栏本就默认隐藏，折叠按钮无意义 */
  .sidebar-toggle{display:none}
  .sidebar-reopen{display:none !important}
  .people-grid{grid-template-columns:1fr}
  .topbar-search input{font-size:16px}  /* iOS 防缩放 */
  .back-to-top{right:14px;bottom:14px;width:38px;height:38px}
}
/* 超窄屏：隐藏字号控制（移动端 pinch zoom 更自然） */
@media(max-width:560px){
  .font-btn{display:none}
}

/* 打印 / PDF：隐藏一切交互元素，展开 details，全宽 */
@media print{
  .sidebar,.topbar,.reading-progress,.back-to-top,
  .sidebar-reopen,.seg-tabs,.sidebar-toggle{display:none !important}
  body{background:#fff;color:#000;font-size:12pt;line-height:1.6}
  main{
    margin-left:0 !important;max-width:none !important;
    padding:0 !important;width:auto;
  }
  section{margin-bottom:24px;break-inside:avoid;page-break-inside:avoid}
  .card,.analysis-card,.method-card,.glossary-card,
  .people-card,.people-detail-card,.map-fig,.dim-lane,.thread,
  .block-quotes,.insight-card,.raw-details,.databars{
    break-inside:avoid;page-break-inside:avoid;
    box-shadow:none !important;
  }
  /* 展开所有 details（真正展开在 JS beforeprint 钩子里） */
  details.raw-details > summary{list-style:none}
  details.raw-details > summary::before{content:""}
  /* 链接和文字保持黑白色 */
  a{color:#000;text-decoration:underline}
  .quote,.block-quotes{background:#fafafa !important;color:#000 !important}
  .quote .ts,.method-card .card-num{background:#666 !important;color:#fff !important}
  mark.srch{background:transparent}
  [data-theme="dark"]{--bg:#fff;--surface:#fff;--text:#000;--muted:#444;--border:#ccc;--accent:#000}
}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-brand">聊聊AI工业应用
      <small>5 小时全场整理 · 9 段 + 5 加工模块</small>
    </div>
    <nav>
      <a href="#overview">总览</a>
      <a href="#people">人物角色卡（4 人）</a>
      <a href="#map">议题关联地图</a>
      <a href="#insights">洞察卡片（10 张）</a>
      <a href="#method">方法论清单（14 卡）</a>
      <div class="nav-group">
        <div class="nav-group-title">9 段主题</div>
        <a href="#seg1">第1段 · 工业方案批评</a>
        <a href="#seg2">第2段 · FDE 模式</a>
        <a href="#seg3">第3段 · Loop Engineer</a>
        <a href="#seg4">第4段 · 价格战</a>
        <a href="#seg5">第5段 · 生图 · 平台</a>
        <a href="#seg6">第6段 · 安全合规</a>
        <a href="#seg7">第7段 · 宏观泡沫</a>
        <a href="#seg8">第8段 · 短视频商业</a>
        <a href="#seg9">第9段 · 人格控制</a>
      </div>
      <a href="#glossary">术语表（32 条）</a>
      <a href="#data">关键数据（53 条）</a>
    </nav>
    <div class="sidebar-foot" style="margin-top:14px;padding:10px 12px;border-top:1px solid var(--border);font-size:11px;color:var(--muted)">完整逐字稿见 <span class="mono">01_清洗稿.md</span></div>
  </aside>
  <main>
    <div class="topbar">
      <div class="topbar-group topbar-left">
        <button class="icon hamburger" id="hamburgerBtn" aria-label="菜单">☰</button>
        <button class="icon sidebar-toggle" id="sidebarToggleBtn" aria-label="折叠侧栏" title="折叠/展开侧栏">⟨</button>
      </div>
      <div class="topbar-search">
        <input id="search" type="search" placeholder="搜索全场关键词…（金句 / 时间戳 / 人名 / 术语）" autocomplete="off">
        <span class="count" id="searchCount"></span>
        <button class="icon search-nav-btn" id="searchPrev" aria-label="上一个匹配" title="上一个 (Shift+回车)">◀</button>
        <button class="icon search-nav-btn" id="searchNext" aria-label="下一个匹配" title="下一个 (回车)">▶</button>
      </div>
      <div class="topbar-group topbar-right">
        <button class="icon font-btn" id="fontDec" aria-label="缩小字号" title="缩小字号">A−</button>
        <button class="icon font-btn" id="fontInc" aria-label="放大字号" title="放大字号">A+</button>
        <button class="icon" id="themeBtn" aria-label="切换主题" title="切换深浅主题">🌙</button>
      </div>
    </div>

    <!--SECTIONS-->

  </main>
</div>

<!-- 阅读进度条（页面最顶端） -->
<div class="reading-progress" id="readingProgress" aria-hidden="true"></div>

<!-- 折叠侧栏后左上角的展开按钮 -->
<button class="icon sidebar-reopen" id="sidebarReopen" aria-label="展开侧栏" title="展开侧栏">⟩</button>

<!-- 回到顶部按钮（右下浮动） -->
<button class="icon back-to-top" id="backToTop" aria-label="回到顶部" title="回到顶部">↑</button>

<script>
// ============================================================
// 1. scrollspy —— 滚动时高亮侧栏当前段
// ============================================================
(function(){
  const navLinks = Array.from(document.querySelectorAll('.sidebar nav a[href^="#"]'));
  const linkMap = new Map();
  navLinks.forEach(a=>{
    const id=a.getAttribute('href').slice(1);
    const sec=document.getElementById(id);
    if(sec) linkMap.set(sec,a);
  });
  const obs = new IntersectionObserver(entries=>{
    entries.forEach(e=>{
      if(e.isIntersecting){
        navLinks.forEach(l=>l.classList.remove('active'));
        const a=linkMap.get(e.target);
        if(a) a.classList.add('active');
      }
    });
  },{rootMargin:'-15% 0px -75% 0px',threshold:0});
  linkMap.forEach((a,sec)=>obs.observe(sec));
})();

// ============================================================
// 2. 平滑跳转 + 关闭移动端菜单
// ============================================================
(function(){
  document.querySelectorAll('.sidebar nav a').forEach(a=>{
    a.addEventListener('click',e=>{
      const href=a.getAttribute('href');
      if(!href.startsWith('#')) return;
      const target=document.querySelector(href);
      if(!target) return;
      e.preventDefault();
      target.scrollIntoView({behavior:'smooth',block:'start'});
      document.getElementById('sidebar').classList.remove('open');
      history.replaceState(null,'',href);
    });
  });
  document.getElementById('hamburgerBtn').addEventListener('click',()=>{
    document.getElementById('sidebar').classList.toggle('open');
  });
})();

// ============================================================
// 3. 深浅主题切换（localStorage 记忆）
// ============================================================
(function(){
  const themeBtn=document.getElementById('themeBtn');
  const root=document.documentElement;
  function apply(t){
    if(t==='dark'){root.setAttribute('data-theme','dark');themeBtn.textContent='☀️';}
    else{root.removeAttribute('data-theme');themeBtn.textContent='🌙';}
  }
  apply(localStorage.getItem('theme'));
  themeBtn.addEventListener('click',()=>{
    const cur=root.getAttribute('data-theme')==='dark'?'light':'dark';
    localStorage.setItem('theme',cur);
    apply(cur);
  });
})();

// ============================================================
// 4. 金句卡点击复制到剪贴板
// ============================================================
(function(){
  document.querySelectorAll('.quote').forEach(q=>{
    q.addEventListener('click',()=>{
      const text=q.innerText.replace(/^复制\\s*/,'').trim();
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(text).then(()=>{
          q.classList.add('copied');
          setTimeout(()=>q.classList.remove('copied'),1500);
        }).catch(()=>{});
      } else {
        // 兜底
        const ta=document.createElement('textarea');
        ta.value=text;document.body.appendChild(ta);ta.select();
        try{document.execCommand('copy');}catch(e){}
        document.body.removeChild(ta);
        q.classList.add('copied');
        setTimeout(()=>q.classList.remove('copied'),1500);
      }
    });
  });
})();

// ============================================================
// 5. 时间戳点击跳清洗稿并临时高亮
// ============================================================
(function(){
  document.querySelectorAll('a.ts[data-ts], .quote a[data-ts]').forEach(a=>{
    a.addEventListener('click',e=>{
      e.preventDefault();
      e.stopPropagation();
      const ts=a.getAttribute('data-ts');
      const id='ts-'+ts.replace(/:/g,'-');
      const target=document.getElementById(id);
      if(!target) return;
      target.scrollIntoView({behavior:'smooth',block:'center'});
      // 临时高亮
      target.classList.add('轻量模型');
      // 上滚一点给 sticky topbar 留空
      setTimeout(()=>{
        const y=target.getBoundingClientRect().top+window.scrollY-80;
        window.scrollTo({top:y,behavior:'smooth'});
      },80);
      setTimeout(()=>target.classList.remove('轻量模型'),2600);
    });
  });
  // 原文节选里的时间戳也支持点击
  document.querySelectorAll('.raw-body .line[data-ts] .ts, .transcript .line[data-ts] .ts').forEach(s=>{
    s.style.cursor='pointer';
    s.addEventListener('click',e=>{
      const line=e.target.closest('.line');
      if(!line) return;
      line.classList.add('轻量模型');
      setTimeout(()=>line.classList.remove('轻量模型'),2600);
    });
  });
})();

// ============================================================
// 6. 关键数据表头点击排序
// ============================================================
(function(){
  document.querySelectorAll('#data table.sortable').forEach(table=>{
    const thead=table.querySelector('thead');
    if(!thead) return;
    let lastIdx=-1,lastDir=1;
    thead.addEventListener('click',e=>{
      const th=e.target.closest('th');
      if(!th) return;
      const ths=Array.from(thead.querySelectorAll('th'));
      const idx=ths.indexOf(th);
      if(idx<0) return;
      const dir=(idx===lastIdx)?-lastDir:1;
      lastIdx=idx;lastDir=dir;
      ths.forEach(t=>t.classList.remove('sort-asc','sort-desc'));
      th.classList.add(dir>0?'sort-asc':'sort-desc');
      const tbody=table.querySelector('tbody');
      if(!tbody) return;
      const rows=Array.from(tbody.querySelectorAll('tr'));
      rows.sort((ra,rb)=>{
        const a=ra.children[idx]?.innerText?.trim()||'';
        const b=rb.children[idx]?.innerText?.trim()||'';
        // 尝试数值比较
        const na=parseFloat(a.replace(/[^\\d.\\-]/g,''));
        const nb=parseFloat(b.replace(/[^\\d.\\-]/g,''));
        if(!isNaN(na)&&!isNaN(nb)&&a.match(/\\d/)&&b.match(/\\d/)){
          return (na-nb)*dir;
        }
        return a.localeCompare(b,'zh-CN')*dir;
      });
      rows.forEach(r=>tbody.appendChild(r));
    });
  });
})();

// ============================================================
// 7. 全文搜索 —— 关键词高亮（<mark class="srch">）
// ============================================================
(function(){
  const input=document.getElementById('search');
  const countEl=document.getElementById('searchCount');
  // 把上一次的高亮还原：用 data-srch 标记的 mark 替换回原文
  function clearHighlights(){
    document.querySelectorAll('main mark.srch').forEach(m=>{
      const txt=document.createTextNode(m.textContent);
      m.parentNode.replaceChild(txt,m);
    });
    // 合并相邻文本节点
    document.querySelectorAll('main section').forEach(s=>s.normalize());
  }
  function escapeRegExp(s){return s.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&');}
  function highlightIn(node,re){
    let count=0;
    const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT,{
      acceptNode(n){
        if(!n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        // 跳过 script/style
        const p=n.parentNode;
        if(!p) return NodeFilter.FILTER_REJECT;
        const tag=p.tagName;
        if(tag==='SCRIPT'||tag==='STYLE') return NodeFilter.FILTER_REJECT;
        return re.test(n.nodeValue)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT;
      }
    });
    const targets=[];
    while(walker.nextNode()) targets.push(walker.currentNode);
    targets.forEach(n=>{
      const frag=document.createDocumentFragment();
      let last=0;
      const s=n.nodeValue;
      re.lastIndex=0;
      let m;
      while((m=re.exec(s))!==null){
        if(m.index>last) frag.appendChild(document.createTextNode(s.slice(last,m.index)));
        const mk=document.createElement('mark');
        mk.className='srch';
        mk.textContent=m[0];
        frag.appendChild(mk);
        last=m.index+m[0].length;
        count++;
        if(m.index===re.lastIndex) re.lastIndex++;  // 防止零宽死循环
      }
      if(last<s.length) frag.appendChild(document.createTextNode(s.slice(last)));
      n.parentNode.replaceChild(frag,n);
    });
    return count;
  }
  const prevBtn=document.getElementById('searchPrev');
  const nextBtn=document.getElementById('searchNext');
  const OFFSET=110;  // topbar + seg-tabs sticky 高度 + 余量
  let hits=[];       // 当前命中的 mark 元素数组
  let curIdx=-1;

  function updateCurrent(){
    document.querySelectorAll('main mark.srch.cur').forEach(m=>m.classList.remove('cur'));
    if(curIdx>=0 && hits[curIdx]) hits[curIdx].classList.add('cur');
  }
  function updateCount(){
    const q=input.value.trim();
    if(!hits.length){
      countEl.textContent = q ? '0/0' : '';
      countEl.className = 'count' + (q ? ' none' : '');
      prevBtn.disabled=true;
      nextBtn.disabled=true;
      return;
    }
    countEl.textContent=(curIdx+1)+'/'+hits.length;
    countEl.className='count';
    prevBtn.disabled=false;
    nextBtn.disabled=false;
  }
  function jumpTo(idx){
    if(!hits.length) return;
    // 负数和越界都循环
    curIdx=((idx % hits.length) + hits.length) % hits.length;
    updateCurrent();
    const el=hits[curIdx];
    const y=el.getBoundingClientRect().top + window.scrollY - OFFSET;
    window.scrollTo({top:y,behavior:'smooth'});
    updateCount();
  }

  let timer=null;
  input.addEventListener('input',()=>{
    clearTimeout(timer);
    timer=setTimeout(run,180);
  });
  input.addEventListener('keydown',e=>{
    if(e.key==='Enter'){
      e.preventDefault();
      if(!hits.length) return;
      if(e.shiftKey) jumpTo(curIdx-1);
      else jumpTo(curIdx+1);
    }
  });
  prevBtn.addEventListener('click',()=>{if(hits.length) jumpTo(curIdx-1);});
  nextBtn.addEventListener('click',()=>{if(hits.length) jumpTo(curIdx+1);});

  function run(){
    clearHighlights();
    curIdx=-1;
    const q=input.value.trim();
    if(!q){hits=[];updateCount();return;}
    let re;
    try{ re=new RegExp(escapeRegExp(q),'gi'); }
    catch(e){ hits=[]; updateCount(); return; }
    document.querySelectorAll('main section').forEach(sec=>{
      // 跳过隐藏的 details 内容（折叠态不搜），可选：仍然搜
      highlightIn(sec,re);
    });
    hits=Array.from(document.querySelectorAll('main mark.srch'));
    if(hits.length){
      jumpTo(0);  // 自动跳第一个并标记为当前
    } else {
      updateCount();
    }
  }
  // 初始状态
  updateCount();
})();

// ============================================================
// 8. seg-tabs 段内导航：点击平滑滚动（带 sticky 偏移）+ 高亮当前块
// ============================================================
(function(){
  const OFFSET = 110; // topbar + seg-tabs sticky 高度 + 余量
  document.querySelectorAll('.seg-tabs').forEach(tabs=>{
    const chips = Array.from(tabs.querySelectorAll('.chip'));
    const chipMap = new Map();  // target el -> chip
    chips.forEach(c=>{
      const id = c.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if(el) chipMap.set(el, c);
      c.addEventListener('click',e=>{
        e.preventDefault();
        if(!el) return;
        // 目标是 details 且未展开 → 先展开再滚
        if(el.tagName === 'DETAILS' && !el.open) el.open = true;
        const y = el.getBoundingClientRect().top + window.scrollY - OFFSET;
        window.scrollTo({top:y, behavior:'smooth'});
        // 临时高亮
        chips.forEach(x=>x.classList.remove('active'));
        c.classList.add('active');
        history.replaceState(null,'', '#' + id);
      });
    });
    if(!chipMap.size) return;
    // 独立 observer，只观察本段的 4 个块，不与侧栏 scrollspy 冲突
    const obs = new IntersectionObserver(entries=>{
      // 选当前最靠近视口顶部的可见块
      let best=null, bestTop=Infinity;
      entries.forEach(en=>{
        if(en.isIntersecting){
          const t=en.boundingClientRect.top;
          if(t<bestTop){bestTop=t;best=en.target;}
        }
      });
      if(best){
        chips.forEach(x=>x.classList.remove('active'));
        const c=chipMap.get(best);
        if(c) c.classList.add('active');
      }
    },{rootMargin:'-'+OFFSET+'px 0px -65% 0px',threshold:0});
    chipMap.forEach((c,el)=>obs.observe(el));
  });
})();

// ============================================================
// 9. Esc 关闭移动端菜单
// ============================================================
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    document.getElementById('sidebar').classList.remove('open');
  }
});

// ============================================================
// 9b. 锚点跳入折叠区时自动展开 details（v2.3.2 详析默认折叠的配套，
//     否则②层/侧栏/seg-tabs 的跳转会被折叠吞掉）
// ============================================================
document.addEventListener('click',e=>{
  const a=e.target.closest('a[href^="#"]');
  if(!a)return;
  const t=document.getElementById(a.getAttribute('href').slice(1));
  if(!t)return;
  for(let el=t;el;el=el.parentElement){
    if(el.tagName==='DETAILS'&&!el.open){el.open=true;}
  }
});

// ============================================================
// 10. 顶部阅读进度条 —— 随滚动更新宽度
// ============================================================
(function(){
  const bar=document.getElementById('readingProgress');
  if(!bar) return;
  let ticking=false;
  function update(){
    const h=document.documentElement;
    const scrollH=document.documentElement.scrollHeight - window.innerHeight;
    const pct = scrollH>0 ? (window.scrollY / scrollH) * 100 : 0;
    bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
    ticking=false;
  }
  window.addEventListener('scroll',()=>{
    if(!ticking){
      window.requestAnimationFrame(update);
      ticking=true;
    }
  },{passive:true});
  window.addEventListener('resize',update,{passive:true});
  update();
})();

// ============================================================
// 11. 回到顶部按钮 —— 滚过一屏后淡入，点击平滑回顶
// ============================================================
(function(){
  const btn=document.getElementById('backToTop');
  if(!btn) return;
  let ticking=false;
  function onScroll(){
    const showThreshold = window.innerHeight * 0.9;
    if(window.scrollY > showThreshold) btn.classList.add('show');
    else btn.classList.remove('show');
    ticking=false;
  }
  window.addEventListener('scroll',()=>{
    if(!ticking){
      window.requestAnimationFrame(onScroll);
      ticking=true;
    }
  },{passive:true});
  btn.addEventListener('click',()=>{
    window.scrollTo({top:0,behavior:'smooth'});
  });
  onScroll();
})();

// ============================================================
// 12. 字号控制 A− / A+ —— 调整根 font-size，localStorage 记忆
// ============================================================
(function(){
  const dec=document.getElementById('fontDec');
  const inc=document.getElementById('fontInc');
  if(!dec || !inc) return;
  const BASE=15, MIN=13, MAX=18, STEP=1;  // 基准 15px，范围 13-18px
  function apply(scale){
    const px = BASE + scale * STEP;
    document.documentElement.style.fontSize = px + 'px';
  }
  // 读取存档
  let scale = parseInt(localStorage.getItem('font-scale') || '0', 10);
  if(isNaN(scale)) scale = 0;
  scale = Math.max(MIN-BASE, Math.min(MAX-BASE, scale));
  apply(scale);
  dec.addEventListener('click',()=>{
    if(scale > MIN-BASE){scale--;apply(scale);localStorage.setItem('font-scale',String(scale));}
  });
  inc.addEventListener('click',()=>{
    if(scale < MAX-BASE){scale++;apply(scale);localStorage.setItem('font-scale',String(scale));}
  });
})();

// ============================================================
// 13. 侧栏折叠 —— body.sidebar-collapsed，localStorage 记忆
//     桌面专用；窄屏（侧栏本就默认隐藏）按钮不显示
// ============================================================
(function(){
  const toggleBtn=document.getElementById('sidebarToggleBtn');
  const reopenBtn=document.getElementById('sidebarReopen');
  const body=document.body;
  const KEY='sidebar-collapsed';

  function setCollapsed(c){
    if(c) body.classList.add('sidebar-collapsed');
    else body.classList.remove('sidebar-collapsed');
    try{ localStorage.setItem(KEY, c ? '1' : '0'); }catch(e){}
  }

  // 初始读取（仅桌面）
  if(window.matchMedia('(min-width:821px)').matches){
    try{
      if(localStorage.getItem(KEY)==='1') setCollapsed(true);
    }catch(e){}
  }

  if(toggleBtn){
    toggleBtn.addEventListener('click',()=>{
      setCollapsed(!body.classList.contains('sidebar-collapsed'));
    });
  }
  if(reopenBtn){
    reopenBtn.addEventListener('click',()=>{
      setCollapsed(false);
    });
  }
})();

// ============================================================
// 14. 打印钩子 —— 打印前展开所有 details，打印后恢复
// ============================================================
(function(){
  let openedDetails=[];
  window.addEventListener('beforeprint',()=>{
    openedDetails=[];
    document.querySelectorAll('details').forEach(d=>{
      if(!d.open){
        d.open=true;
        openedDetails.push(d);
      }
    });
  });
  window.addEventListener('afterprint',()=>{
    openedDetails.forEach(d=>{d.open=false;});
    openedDetails=[];
  });
})();
</script>
</body>
</html>
"""




if __name__ == "__main__":
    main()
