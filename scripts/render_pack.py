#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recording Knowledge Pack — 通用渲染 wrapper。

读一个"场次目录"（按规范放好 01-09 的 md），自动提取配置，一键生成自包含 index.html。
任何场次零配置：段标题/人物/母题/各类计数全部从 md 自动提取。

用法：
    python render_pack.py <场次目录> [--brand "显示名"]

场次目录结构（详见 SKILL.md）：
    <场次目录>/
      00_总览.md                 (可选；没有则自动生成骨架)
      01_清洗稿.md               (可选；不进 HTML，仅作素材)
      02_主题整理/第1段_*.md ... 第N段_*.md
      03_方法论清单.md
      04_术语表.md
      05_人物角色卡.md
      06_关键数据速查.md
      07_议题关联地图.md
      08_洞察卡片.md
      09_战略诊断与行动清单.md   (可选；咨询/诊断类才有)

依赖：同目录 build_html.py（渲染器母版，自带 CSS/JS/通用渲染）。
"""
import sys
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_html as B  # noqa: E402  渲染器母版

PALETTE = [
    ("#3370ff", "蓝"), ("#00b894", "绿"), ("#e8910a", "橙"),
    ("#8a5cf6", "紫"), ("#e5404e", "红"), ("#16a34a", "青"),
    ("#0ea5e9", "天"), ("#d97706", "琥"),
]


# ============================================================
# 渲染含 ``` 代码块（ASCII 图）的 md
# ============================================================
def render_md_with_code(md, sortable=False):
    """按 ``` 切分：代码块→<pre class="ascii-map">，其余→母版通用渲染。"""
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        if lines[i].strip().startswith("```"):
            i += 1
            code = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            i += 1  # 跳过结束 ```
            out.append(f'<pre class="ascii-map">{B.esc(chr(10).join(code))}</pre>')
        else:
            chunk = []
            while i < n and not lines[i].strip().startswith("```"):
                chunk.append(lines[i]); i += 1
            if any(ln.strip() for ln in chunk):
                out.append(B.render_blocks_generic(
                    B.md_to_blocks(chr(10).join(chunk)), sortable_tables=sortable))
    return "\n".join(out)


def strip_h1(md):
    return re.sub(r"^#\s+.+\n+", "", md, count=1)


# ============================================================
# 自动提取
# ============================================================
def extract_seg_meta(seg_dir):
    meta = {}
    for i in range(1, 30):
        files = sorted(seg_dir.glob(f"第{i}段_*.md"))
        if not files:
            break
        md = files[0].read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = m.group(1).strip() if m else f"第{i}段"
        # 副标题优先级：> 副标题： > 摘要首句(截50字) > 时段的时间部分
        sub = ""
        ms = re.search(r"^>\s*副标题[：:]\s*(.+)$", md, re.M)
        if ms:
            sub = ms.group(1).strip()
        else:
            msm = re.search(r"^##\s*摘要\s*\n+\s*(.+?)$", md, re.M)
            if msm:
                sub = msm.group(1).strip()[:50]
            else:
                mst = re.search(r"^>\s*时段[：:]\s*(.+?)\s*(?:｜|\|)", md, re.M)
                if mst:
                    sub = mst.group(1).strip()
        meta[i] = (title, sub)
    return meta


def extract_people(people_md):
    people = []
    for blk in re.split(r"(?=^##\s+)", people_md, flags=re.M):
        m = re.match(r"^##\s+(.+?)$", blk, re.M)
        if not m:
            continue
        name = m.group(1).strip()
        if not name or name.startswith("人物") or "角色卡" in name:
            continue
        rm = re.search(r"约\s*(\d+)\s*%", blk)
        ratio = int(rm.group(1)) if rm else 0
        # tagline 优先用"角色标签"（更精炼），否则回退"背景与立场"首句
        tag = ""
        tm = re.search(r"\*\*角色标签\*\*[：:]\s*(.+)$", blk, re.M)
        if not tm:
            tm = re.search(r"\*\*背景与立场\*\*[：:]\s*(.+)$", blk, re.M)
        if tm:
            tag = tm.group(1).strip()[:80]
        people.append({"name": name, "ratio": ratio, "tag": tag})
    for idx, p in enumerate(people):
        c, _ = PALETTE[idx % len(PALETTE)]
        p["color"] = c
        p["initial"] = p["name"][0] if p["name"] else "?"
    return people


def count_heading(md, pattern):
    return len(re.findall(pattern, md, flags=re.M)) if md else 0


def extract_mother(map_md):
    m = re.search(r"\*\*母题\*\*[：:]\s*(.+)$", map_md, re.M)
    return m.group(1).strip() if m else ""


# ============================================================
# 通用渲染函数（monkey-patch 母版写死的部分）
# ============================================================
def make_render_overview(seg_meta, people, mother, brand):
    def render_overview():
        parts = [f'<h2 class="seg-title">{B.esc(brand)}</h2>',
                 '<p class="seg-subtitle">总览 · 本场在讲什么</p>']
        if mother:
            parts.append(f'<div class="card overview-card"><h3>母题</h3>'
                         f'<p>{B.inline_fmt(mother)}</p></div>')
        if people:
            parts.append('<div class="card overview-card"><h3>发言者</h3><ul class="people-quick">')
            for p in people:
                tail = f'（约 {p["ratio"]}%）' if p["ratio"] else ""
                parts.append(f'<li><strong style="color:{p["color"]}">{B.esc(p["name"])}</strong>'
                             f'{(" · " + B.esc(p["tag"])) if p["tag"] else ""}{tail}</li>')
            parts.append('</ul></div>')
        if seg_meta:
            parts.append('<div class="card overview-card"><h3>分段目录</h3><ol class="seg-toc">')
            for i in sorted(seg_meta):
                parts.append(f'<li><a href="#seg{i}"><strong>{B.inline_fmt(seg_meta[i][0])}</strong></a></li>')
            parts.append('</ol></div>')
        parts.append('<div class="card overview-card"><h3>导航</h3>'
                     '<p class="hint">左侧栏选模块；金句可点复制；时间戳可点跳清洗稿；'
                     '右上角搜索全文高亮；右上角按钮切深色。</p></div>')
        return "\n".join(parts)
    return render_overview


def render_map_generic(map_md):
    out = ['<h2 class="seg-title">议题关联地图</h2>',
           '<p class="seg-subtitle">母题、分层结构与呼应</p>']
    out.append(render_md_with_code(strip_h1(map_md)))
    return "\n".join(out)


def render_data_generic(data_md):
    out = ['<h2 class="seg-title">关键数据速查</h2>',
           '<p class="seg-subtitle">点击表头排序</p>']
    out.append(render_md_with_code(strip_h1(data_md), sortable=True))
    return "\n".join(out)


def render_people_generic(people_md, people):
    out = ['<h2 class="seg-title">人物角色卡</h2>',
           f'<p class="seg-subtitle">{len(people)} 位发言者 · 头像 / 发言量</p>']
    out.append('<div class="people-grid">')
    for p in people:
        out.append(
            f'<div class="card people-card"><div class="people-head">'
            f'<div class="avatar" style="background:{p["color"]}">{B.esc(p["initial"])}</div>'
            f'<div class="people-meta"><div class="people-name">{B.esc(p["name"])}</div></div></div>'
            f'<div class="people-line">{B.esc(p["tag"])}</div>'
            f'<div class="people-bar-wrap"><div class="people-bar-label">发言量 约 {p["ratio"] or "?"}%</div>'
            f'<div class="people-bar-track"><div class="people-bar" style="width:{p["ratio"] or 0}%;background:{p["color"]}"></div></div>'
            f'</div></div>')
    out.append('</div>')
    out.append('<details class="raw-details" open><summary>详细人物角色卡（背景 / 进场 / 本场作用 / 代表发言）</summary>'
               '<div class="raw-body people-detail">')
    blocks = B.md_to_blocks(people_md)
    i, n = 0, len(blocks)
    while i < n:
        kind, payload = blocks[i]
        if kind == "h2":
            name = payload.strip()
            if name.startswith("人物") or "角色卡" in name:
                i += 1; continue
            color = next((p["color"] for p in people if p["name"] == name), "#3370ff")
            out.append(f'<div class="card people-detail-card" style="border-left:4px solid {color}">')
            out.append(f'<h3 class="people-detail-name" style="color:{color}">{B.esc(name)}</h3>')
            j = i + 1
            cb = []
            while j < n and blocks[j][0] != "h2":
                if blocks[j][0] != "blank":
                    cb.append(blocks[j])
                j += 1
            for k2, p2 in cb:
                if k2 == "plain":
                    out.append(f'<p>{B.inline_fmt(p2)}</p>')
                elif k2 == "quote":
                    out.append(f'<blockquote class="people-quote">{B.inline_fmt(p2)}</blockquote>')
                elif k2 == "quote_speaker":
                    out.append(B.render_speaker_line(p2))
                else:
                    out.append(B.render_blocks_generic([(k2, p2)]))
            out.append('</div>')
            i = j
        else:
            i += 1
    out.append('</div></details>')
    return "\n".join(out)


def render_insights_generic(insights_md):
    """渲染洞察卡（含字段头）+ 洞察地图（含 ASCII 图）。"""
    lines = insights_md.split("\n")
    out = ['<h2 class="seg-title">洞察卡片</h2>',
           '<p class="seg-subtitle">反直觉规律 · 核心 + 证据原话 + 启示 + 反方</p>']
    i, n = 0, len(lines)
    while i < n and not lines[i].lstrip().startswith("# "):
        i += 1
    i += 1
    intro = []
    while i < n:
        s = lines[i].rstrip()
        if s.startswith("## ") or re.match(r"^-{3,}\s*$", s):
            break
        m = re.match(r"^>\s?(.*)$", s)
        if m:
            intro.append(m.group(1))
        i += 1
    if intro:
        out.append(f'<blockquote>{B.inline_fmt(" ".join(intro))}</blockquote>')
    while i < n and re.match(r"^-{3,}\s*$", lines[i].rstrip()):
        i += 1
    while i < n:
        s = lines[i].rstrip()
        if s.startswith("## "):
            heading = s[3:].strip()
            if heading == "洞察地图":
                rest = "\n".join(lines[i + 1:])
                out.append('<h3 class="block-h">洞察地图</h3>')
                out.append(render_md_with_code(rest))
                break
            m = re.match(r"^卡\s*(?P<num>\d+)\s*[·•・]?\s*(?P<name>.+?)\s*$", heading)
            if m:
                num, name = m.group("num"), m.group("name")
                i += 1
                cl = []
                while (i < n and not lines[i].rstrip().startswith("## ")
                       and not re.match(r"^-{3,}\s*$", lines[i].rstrip())):
                    cl.append(lines[i]); i += 1
                while i < n and re.match(r"^-{3,}\s*$", lines[i].rstrip()):
                    i += 1
                out.append(B.render_insight_card(num, name, chr(10).join(cl)))
            else:
                i += 1
        else:
            i += 1
    return "\n".join(out)


def build_sidebar(brand, seg_meta, counts, has_strategy):
    nav = ['<a href="#overview">总览</a>',
           f'<a href="#people">人物角色卡（{counts["people"]} 人）</a>',
           '<a href="#map">议题关联地图</a>',
           f'<a href="#insights">洞察卡片（{counts["insights"]} 张）</a>',
           f'<a href="#method">方法论清单（{counts["method"]} 卡）</a>']
    if seg_meta:
        nav.append('<div class="nav-group"><div class="nav-group-title">主题分段</div>')
        for i in sorted(seg_meta):
            t = seg_meta[i][0]
            short = t.split("·", 1)[-1].strip() if "·" in t else t
            nav.append(f'<a href="#seg{i}">{B.inline_fmt(short)}</a>')
        nav.append('</div>')
    if has_strategy:
        nav.append('<a href="#strategy">战略诊断与行动清单</a>')
    nav.append(f'<a href="#glossary">术语表（{counts["glossary"]} 条）</a>')
    nav.append('<a href="#data">关键数据速查</a>')
    return ('<aside class="sidebar" id="sidebar">'
            f'<div class="sidebar-brand">{B.esc(brand)}'
            '<small>录音知识包 · 结构化整理</small></div>'
            f'<nav>{"".join(nav)}</nav>'
            '<div class="sidebar-foot" style="margin-top:14px;padding:10px 12px;'
            'border-top:1px solid var(--border);font-size:11px;color:var(--muted)">'
            '由 transcript-to-knowledge-pipeline 生成</div></aside>')


# ============================================================
# main
# ============================================================
def main():
    if len(sys.argv) < 2:
        print("用法: python render_pack.py <场次目录> [--brand 显示名]")
        sys.exit(1)
    pack_dir = Path(sys.argv[1]).resolve()
    brand = pack_dir.name
    if "--brand" in sys.argv:
        idx = sys.argv.index("--brand")
        if idx + 1 < len(sys.argv):
            brand = sys.argv[idx + 1]
    seg_dir = pack_dir / "02_主题整理"

    def rd(name):
        p = pack_dir / name
        return p.read_text(encoding="utf-8") if p.exists() else ""

    seg_meta = extract_seg_meta(seg_dir) if seg_dir.exists() else {}
    people_md = rd("05_人物角色卡.md")
    people = extract_people(people_md) if people_md else []
    mother = extract_mother(rd("07_议题关联地图.md"))
    has_strategy = (pack_dir / "09_战略诊断与行动清单.md").exists()
    counts = {
        "people": len(people),
        "insights": count_heading(rd("08_洞察卡片.md"), r"^##\s+卡\s*\d+"),
        "method": count_heading(rd("03_方法论清单.md"), r"^##\s+\d+\."),
        "glossary": count_heading(rd("04_术语表.md"), r"^###\s+"),
    }

    # monkey-patch 母版
    B.SEG_META = seg_meta or {1: ("第1段", "")}
    B.sp_color = lambda s: "x"
    overview_md = rd("00_总览.md")
    if overview_md:
        # 有定制总览就用它（00_总览.md）
        _ov_body = render_md_with_code(strip_h1(overview_md))
        B.render_overview = lambda b=_ov_body: b
    else:
        B.render_overview = make_render_overview(seg_meta, people, mother, brand)
    B.render_map = lambda md: render_map_generic(md)
    B.render_data = lambda md: render_data_generic(md)
    B.render_people = lambda md: render_people_generic(md, people)
    B.render_insights = lambda md: render_insights_generic(md)

    # 组装 sections
    sections = []
    sections.append('    <section id="overview">\n' + B.render_overview() + '\n    </section>')
    if people_md:
        sections.append('    <section id="people">\n' + B.render_people(people_md) + '\n    </section>')
    if rd("07_议题关联地图.md"):
        sections.append('    <section id="map">\n' + B.render_map(rd("07_议题关联地图.md")) + '\n    </section>')
    if rd("08_洞察卡片.md"):
        sections.append('    <section id="insights">\n' + B.render_insights(rd("08_洞察卡片.md")) + '\n    </section>')
    if rd("03_方法论清单.md"):
        sections.append('    <section id="method">\n' + B.render_method(rd("03_方法论清单.md")) + '\n    </section>')
    if seg_dir.exists():
        for sf in sorted(seg_dir.glob("第*段_*.md"),
                         key=lambda p: int(re.search(r"第(\d+)段", p.name).group(1))):
            i = int(re.search(r"第(\d+)段", sf.name).group(1))
            sections.append(f'    <section id="seg{i}">\n' + B.render_seg(i, sf.read_text(encoding="utf-8")) + '\n    </section>')
    if has_strategy:
        sections.append('    <section id="strategy">\n<h2 class="seg-title">战略诊断与行动清单</h2>'
                        '<p class="seg-subtitle">现状 → 定位 → 路径 → 行动</p>\n'
                        + render_md_with_code(strip_h1(rd("09_战略诊断与行动清单.md")), sortable=True) + '\n    </section>')
    if rd("04_术语表.md"):
        sections.append('    <section id="glossary">\n' + B.render_glossary(rd("04_术语表.md")) + '\n    </section>')
    if rd("06_关键数据速查.md"):
        sections.append('    <section id="data">\n' + B.render_data(rd("06_关键数据速查.md")) + '\n    </section>')

    tpl = B.TEMPLATE.replace("    <!--SECTIONS-->", "\n\n".join(sections))
    sidebar = build_sidebar(brand, seg_meta, counts, has_strategy)
    html_out = re.sub(r'<aside class="sidebar".*?</aside>', sidebar, tpl, count=1, flags=re.S)
    # 修母版里写死首场的标题/副标题
    html_out = html_out.replace("<title>聊聊AI工业应用 · 全场整理</title>",
                                f"<title>{brand} · 全场整理</title>")
    html_out = html_out.replace("Harry 方法论清单", f"{brand} 方法论清单")
    html_out = html_out.replace("14 张可复用的思维工具卡 · 定义 + 出处 + 怎么用",
                                "方法论卡 · 定义 + 出处 + 怎么用")

    out_path = pack_dir / "index.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"✓ 已生成 {out_path}（{out_path.stat().st_size / 1024:.1f} KB）")
    print(f"  段:{len(seg_meta)} 人:{counts['people']} 洞察:{counts['insights']} "
          f"方法论:{counts['method']} 术语:{counts['glossary']} 战略诊断:{'有' if has_strategy else '无'}")


if __name__ == "__main__":
    main()
