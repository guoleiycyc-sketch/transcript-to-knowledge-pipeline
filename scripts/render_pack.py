#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recording Knowledge Pack — 通用渲染 wrapper。

读一个"场次目录"（按规范放好 01-09 的 md），自动提取配置，一键生成自包含 index.html。
任何场次零配置：段标题/人物/母题/各类计数全部从 md 自动提取。

版本（仅记渲染器层变更，skill 整体版本见 SKILL.md / CHANGELOG.md）：
    v2.3.8（2026-09-06）三层阅读 v2：①执行摘要升级为醒目可折叠摘要卡（局势+决策
      要点+待办表精简+风险行全 BLUF 入卡，卡底「跳过摘要，看全库内容 ↓」锚）；
      ②总结层改为「分段速览」行卡（各段 ## 摘要 一行一段+「展开该段」下潜）；
      层间锚点：卡内人名→#people、Owner 列→#people、卡N→#insight-N（圈号①-⑳
      原生已链接）。无 00_执行摘要 的老场整块三层导航不渲染（与旧版结构一致）。
    v2.3.7 输出文件名=场次目录名（不再产 index.html）。

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

Safety: Python stdlib only - no network access, no subprocess, no dynamic execution; reads/writes stay within the user's working and output directories.
"""
import sys
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_html as B  # noqa: E402  渲染器母版

# 人物头像色。前三色对比度换深一档：旧 #3370ff(4.3:1)/#00b894(2.5:1)/#e8910a(2.5:1)
# 在白底上不达标（2026-08-19 客户丁场 polish 实测，缺陷 5）
PALETTE = [
    ("#2b62d6", "蓝"), ("#0c7f63", "绿"), ("#9a5f00", "橙"),
    ("#8a5cf6", "紫"), ("#e5404e", "红"), ("#16a34a", "青"),
    ("#0ea5e9", "天"), ("#d97706", "琥"),
]


# ============================================================
# 渲染含 ``` 代码块（ASCII 图）的 md
# ============================================================
def render_md_with_code(md, sortable=False):
    """按 ``` 切分：代码块先尝试图形化解析（分层/线路），失败回退深色终端卡。"""
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        if lines[i].strip().startswith("```"):
            i += 1
            code = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            i += 1  # 跳过结束 ```
            graph = try_render_graph(chr(10).join(code))
            if graph:
                out.append(graph)
            else:
                out.append(f'<pre class="ascii-map">{B.esc(chr(10).join(code))}</pre>')
        else:
            chunk = []
            while i < n and not lines[i].strip().startswith("```"):
                chunk.append(lines[i]); i += 1
            if any(ln.strip() for ln in chunk):
                out.append(B.render_blocks_generic(
                    B.md_to_blocks(chr(10).join(chunk)), sortable_tables=sortable))
    return "\n".join(out)


# ============================================================
# v2.3.3 ASCII 结构图 → 图形化（解析成功出图形，失败回退终端卡）
# 支持两种范式：①分层带（层名行+圈号条目行，作者常在行尾标「—— 绿」颜色意图）
# ②线路流（含 ≥2 个 → 的行）。圈号①-⑳ 与 卡N 自动变可点节点。
# ============================================================
GL_COLORS = {"红": "#e5484d", "橙": "#e8871e", "黄": "#d4a72c", "绿": "#30a46c",
             "蓝": "#3b82f6", "紫": "#8e4ec6", "青": "#12a594"}
GL_FALLBACK_COLOR = "#3b82f6"
CIRCLED = {chr(0x2460 + i): i + 1 for i in range(20)}  # ①-⑳ → 1-20

LAYER_RE = re.compile(
    r"^\s*(母题|第[一二三四五六七八九十百]+层|[上下中底顶]层|核心层|表层)\s*[·:：]?\s*"
    r"(?P<desc>[^—]*?)\s*(?:——\s*(?P<color>红|橙|黄|绿|蓝|紫|青))?\s*$")


def _gl_node(tok, color):
    """节点 token → 可点胶囊：⑬ 选型地图→#seg13；卡3 标题→#insight-3；纯文本→span。"""
    tok = tok.strip().rstrip("；;，,。")
    if not tok:
        return ""
    m = re.match(r"^([①-⑳])\s*(.*)$", tok)
    if m:
        num = CIRCLED.get(m.group(1))
        label = (m.group(1) + (" " + m.group(2) if m.group(2) else "")).strip()
        if num:
            return (f'<a class="gl-node" style="--c:{color}" href="#seg{num}">'
                    f'<span class="gl-chip-num" style="background:{color}">{B.esc(m.group(1))}</span>'
                    f'{B.esc(m.group(2))}</a>')
        return f'<span class="gl-node" style="--c:{color}">{B.esc(label)}</span>'
    m = re.match(r"^卡\s*(\d+)\s*(.*)$", tok)
    if m:
        label = "卡" + m.group(1) + (" " + m.group(2) if m.group(2) else "")
        return (f'<a class="gl-node" style="--c:{color}" href="#insight-{m.group(1)}">'
                f'{B.esc(label)}</a>')
    return f'<span class="gl-node" style="--c:{color}">{B.esc(tok)}</span>'


def _parse_layers(code):
    layers, notes = [], []
    cur = None
    for ln in code.split("\n"):
        if not ln.strip():
            continue
        m = LAYER_RE.match(ln)
        if m and (m.group("desc") or m.group("color")) and m.group(1) != "母题":
            cur = {"name": m.group(1), "desc": m.group("desc").strip(),
                   "color": GL_COLORS.get(m.group("color") or "", GL_FALLBACK_COLOR),
                   "items": []}
            layers.append(cur)
            continue
        if m and m.group(1) == "母题":
            continue  # 母题由 section 单独渲染，图中跳过
        stripped = ln.strip()
        if re.match(r"^[①-⑳]", stripped) and cur is not None:
            for tok in re.split(r"\s{2,}", stripped):
                if tok.strip():
                    cur["items"].append(tok.strip())
        elif layers and stripped:
            notes.append(stripped)
    if len(layers) < 2:
        return None
    return layers, notes


def _parse_flows(code):
    flows = []
    for ln in code.split("\n"):
        s = ln.strip()
        if s.count("→") < 2:
            continue
        name = ""
        if "：" in s.split("→")[0]:
            head, _, s = s.partition("：")
            name = re.sub(r"^[\d.、\s\*]*", "", head).strip()
        nodes = [t for t in (x.strip() for x in s.split("→")) if t]
        if len(nodes) >= 2:
            flows.append((name, nodes))
    return flows or None


def try_render_graph(code):
    """尝试把 ASCII 结构图渲染为图形。识别不了返回 None（回退终端卡）。"""
    layers = _parse_layers(code)
    if layers:
        ls, notes = layers
        out = []
        for lay in ls:
            out.append(f'<div class="gl-layer" style="--c:{lay["color"]}">')
            out.append(f'<div class="gl-layer-h"><span class="gl-layer-name">{B.esc(lay["name"])}</span>')
            if lay["desc"]:
                out.append(f'<span class="gl-layer-tag">{B.esc(lay["desc"])}</span>')
            out.append('</div><div class="gl-chips">')
            for it in lay["items"]:
                out.append(_gl_node(it, lay["color"]))
            out.append('</div></div>')
        for nt in notes[:3]:
            out.append(f'<p class="gl-note">{B.esc(nt)}</p>')
        return "\n".join(out)
    flows = _parse_flows(code)
    if flows:
        palette = ["#3b82f6", "#30a46c", "#e8871e", "#8e4ec6", "#e5484d"]
        out = []
        for idx, (name, nodes) in enumerate(flows):
            color = palette[idx % len(palette)]
            out.append(f'<div class="gl-flow">')
            if name:
                out.append(f'<span class="gl-flow-name" style="--c:{color};background:{color}">{B.esc(name)}</span>')
            for k, nd in enumerate(nodes):
                if k:
                    out.append(f'<span class="gl-arr" style="color:{color}">→</span>')
                out.append(_gl_node(nd, color))
            out.append('</div>')
        return "\n".join(out)
    return None


def strip_h1(md):
    return re.sub(r"^#\s+.+\n+", "", md, count=1)


# ============================================================
# 自动提取
# ============================================================
def clip_sub(s: str, limit: int = 50) -> str:
    """副标题句边界截断：在允许范围内取最后一个句终止符处收口；
    找不到终止符才硬截并补省略号。旧版 [:50] 会把句子腰斩在词中间
    （2026-08-19 客户丁场缺陷 1：16 条副标题 12 条句中截断）。"""
    s = s.strip()
    if len(s) <= limit:
        return s
    best = None
    for m in re.finditer(r"[。！？；…][”」』）)]?", s):
        if m.end() <= limit + 6:
            best = m.end()
        else:
            break
    if best:
        out = s[:best].strip()
    else:
        out = s[:limit].rstrip("，、：;:, ") + "……"
    # 截断点可能落在 **加粗** 标记内部，孤儿 ** 会以字面星号泄漏进页面
    if out.count("**") % 2 == 1:
        k = out.rfind("**")
        out = out[:k] + out[k + 2:]
    return out


def extract_seg_meta(seg_dir):
    meta = {}
    for i in range(1, 30):
        files = sorted(seg_dir.glob(f"第{i}段_*.md"))
        if not files:
            break
        md = files[0].read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = m.group(1).strip() if m else f"第{i}段"
        # 副标题优先级：> 副标题： > 摘要首句(句边界截断) > 时段的时间部分
        sub = ""
        ms = re.search(r"^>\s*副标题[：:]\s*(.+)$", md, re.M)
        if ms:
            sub = ms.group(1).strip()
        else:
            msm = re.search(r"^##\s*摘要\s*\n+\s*(.+?)$", md, re.M)
            if msm:
                sub = clip_sub(msm.group(1).strip())
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
        # 过滤说明性小节（如「## 提及未出场（一句话索引）」）——不是人名，
        # 但保留在详细折叠区正常渲染（被提及者一句话有价值）
        if (not name or name.startswith("人物") or "角色卡" in name
                or name.startswith("提及未出场") or "索引" in name or "速查" in name):
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


# 需跨段去重的头注行：`> [标签] 内容` 与 `> 注：/说明：/备注：/说话人映射：`
# 两类（后者常以 `> **注**：` 加粗形态出现，08-19 客户丁场即此形态重复 16 次）
NOTE_LINE_RE = re.compile(
    r"^(>\s*\[[^\]]+\]\s*.+"
    r"|>\s*\*{0,2}(?:注|说明|备注|说话人映射)\*{0,2}\s*[：:].+)$")

def dedupe_asides(md: str, seen: set) -> str:
    """跨段去重逐字相同的头注行——同一条说话人映射注常被复制进每个
    段文件头，旧版会在每个 seg-meta 卡里重复渲染十几次（2026-08-19
    缺陷 2）。只作用于渲染，不改 md 源文件；金句等其他引用行不去重。"""
    kept = []
    for ln in md.split("\n"):
        m = NOTE_LINE_RE.match(ln.strip())
        if m:
            key = m.group(1)
            if key in seen:
                continue
            seen.add(key)
        kept.append(ln)
    return "\n".join(kept)


# ============================================================
# v2.3 三层阅读结构（B 规格，2026-09-03 某场次方法论第 1 条）
# ① 简报 200-300 字 10 秒决策 → ② 总结 ≤1000 字带下潜链接 → ③ 总体完整层
# 设计约束：②层由机器从既有模块编译派生（段结论/卡标题/待办），不新增
# 手写层——「收敛不是删，是索引」，手写总结层会重蹈 P21 跨层复制。
# ============================================================
def first_sentence(s: str, limit: int = 90) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    m = re.match(r"(.{2,limit}?[。！？；])", s)
    if m:
        return m.group(1)
    return s[:limit] + ("……" if len(s) > limit else "")


def slice_between(md: str, start_pat: str, end_pat: str) -> str:
    """取 start_pat 起始到 end_pat 之前（含起始标记行，供 render 保留字段头）。"""
    ms = re.search(start_pat, md, re.M)
    if not ms:
        return ""
    rest = md[ms.start():]
    me = re.search(end_pat, rest, re.M)
    return rest[:me.start()].strip() if me else rest.strip()


def slice_from(md: str, start_pat: str) -> str:
    """从 start_pat 取到文件尾（待办+风险节）。"""
    ms = re.search(start_pat, md, re.M)
    return md[ms.start():].strip() if ms else ""


def _section_body(md: str, header_pat: str) -> str:
    """取 `## xxx` 节正文（到下一个 1-3 级标题前），剥头注 `>` 行。"""
    mh = re.search(header_pat, md, re.M)
    if not mh:
        return ""
    rest = md[mh.end():]
    me = re.search(r"^#{1,3}\s", rest, re.M)
    body = rest[:me.start()].strip() if me else rest.strip()
    return "\n".join(ln for ln in body.split("\n") if not ln.strip().startswith(">")).strip()


def seg_digest_rows(seg_dir, seg_meta):
    """② 分段速览原料：{段号: 摘要句}（v2.3.8，替代 v2.3 的段结论首句）。
    优先级：`## 摘要`（作者手写，句边界截 ~110 字）→ `## 段结论` 首句 → 段副标题。
    三者全缺的段不进行——不做无中生有的机器概括。"""
    out = {}
    if not seg_dir.exists():
        return out
    for f in sorted(seg_dir.glob("第*段_*.md")):
        m = re.search(r"第(\d+)段", f.name)
        if not m:
            continue
        i = int(m.group(1))
        md = f.read_text(encoding="utf-8")
        s = re.sub(r"\s+", " ", _section_body(md, r"^##\s*摘要\s*$"))
        if not s:
            s = re.sub(r"\s+", " ", _section_body(md, r"^##\s*段结论\s*$"))
        if s:
            out[i] = first_sentence(s, limit=100)
        elif seg_meta.get(i, ("", ""))[1]:
            out[i] = seg_meta[i][1]
    return out


def _link_md_refs(md: str, names, insight_nums) -> str:
    """① 摘要卡专用：把卡内的人名 / 洞察卡引用变成 ③ 层下潜链接（md 级改写，
    渲染走 inline_fmt 的 [文本](#锚点) 通道）。已有手写链接段不动；只换名字不改字。
    - 人名（05 卡名，长名优先防子串误伤）→ #people
    - 卡N（本场确有的洞察卡号）→ #insight-N
    - 圈号①-⑳ inline_fmt 原生已是 #segN 链接，无需处理。"""
    if not md:
        return md
    # 按已有 md 链接切段，链接文本不重复包
    parts = re.split(r"(\[[^\]]*\]\([^)]*\))", md)
    names_desc = sorted((n for n in names if len(n) >= 2), key=len, reverse=True)
    for k, part in enumerate(parts):
        if part.startswith("[") and part.rstrip().endswith(")"):
            continue  # 已是 md 链接段，不重复包
        s = part
        for nm in names_desc:
            if nm in s:
                s = s.replace(nm, f"[{nm}](#people)")
        def _card(m):
            return f"[卡{m.group(1)}](#insight-{m.group(1)})" if m.group(1) in insight_nums else m.group(0)
        s = re.sub(r"(?<![\w卡])卡\s*(\d+)(?!\d)", _card, s)
        parts[k] = s
    return "".join(parts)


def _link_owner_cells(md: str) -> str:
    """待办表 Owner 列整格下潜 #people（v2.3.8）。整格可点——覆盖「C/A」
    「部落」等昵称/多人格写法，不依赖 05 卡名精确匹配。"""
    if not md or "|" not in md:
        return md
    lines = md.split("\n")
    hdr_i = next((k for k, ln in enumerate(lines)
                  if ln.lstrip().startswith("|") and re.search(r"Owner|负责|责任", ln)), None)
    if hdr_i is None:
        return md
    hdr_cells = [c.strip() for c in lines[hdr_i].strip().strip("|").split("|")]
    col = next((k for k, c in enumerate(hdr_cells) if re.search(r"Owner|负责|责任", c)), None)
    if col is None:
        return md
    for k in range(hdr_i + 1, len(lines)):
        ln = lines[k]
        if not ln.lstrip().startswith("|") or re.match(r"^\|[\s:|-]+\|\s*$", ln):
            continue
        cells = ln.strip().strip("|").split("|")
        if col < len(cells) and cells[col].strip() and "[" not in cells[col]:
            cells[col] = f" [{cells[col].strip()}](#people) "
            lines[k] = "|" + "|".join(cells) + "|"
    return "\n".join(lines)


def render_brief(exec_md, people_names, insight_nums, library_anchor="#people", has_digest=True):
    """① 简报层 v2.3.8：00_执行摘要全 BLUF 四节收进一张醒目可折叠摘要卡
    （details 默认展开）：局势 → 本场决策要点 → 待办表精简（Owner 可点下潜人物卡）
    → 风险行；卡底「跳过摘要，看全库内容 ↓」锚到③层首模块。写作侧零改动
    （00 仍按 BLUF 四节写），阅读侧三层化。"""
    situation = (slice_between(exec_md, r"^\*\*局势\*\*", r"^\*\*本场决策")
                 or slice_between(exec_md, r"^\*\*局势\*\*", r"^\*\*待办\*\*")
                 or slice_between(exec_md, r"^\*\*局势\*\*", r"^\*\*风险"))
    decisions = slice_between(exec_md, r"^\*\*本场决策", r"^\*\*待办\*\*")
    tail = slice_from(exec_md, r"^\*\*待办\*\*")
    todo_md, risk_md = "", ""
    if tail:
        m = re.search(r"^\*\*风险", tail, re.M)
        if m:
            todo_md, risk_md = tail[:m.start()].strip(), tail[m.start():].strip()
        else:
            todo_md = tail.strip()
    out = ['<details class="brief-card" open>',
           '<summary class="brief-card-sum"><span class="bc-num">①</span>'
           '<span class="bc-title">执行摘要</span>'
           '<span class="bc-hint">局势 · 决策 · 待办 · 风险 —— 读完这张卡就够，不够再下潜</span></summary>',
           '<div class="brief-card-body">']
    if situation:
        out.append('<div class="bc-sec">'
                   + render_md_with_code(_link_md_refs(situation, people_names, insight_nums))
                   + '</div>')
    elif not decisions and not todo_md:
        # 非 BLUF 形态的 00（极少）：整文渲染兜底
        out.append('<div class="bc-sec">' + render_md_with_code(strip_h1(exec_md)) + '</div>')
    if decisions:
        out.append('<div class="bc-sec">'
                   + render_md_with_code(_link_md_refs(decisions, people_names, insight_nums))
                   + '</div>')
    if todo_md:
        # 待办表精简：紧凑表格（CSS 压字号/行距），Owner 列可点，表头仍可排序
        out.append('<div class="bc-sec bc-todo">'
                   + render_md_with_code(_link_owner_cells(todo_md), sortable=True) + '</div>')
    if risk_md:
        out.append('<div class="bc-sec bc-risk">'
                   + render_md_with_code(_link_md_refs(risk_md, people_names, insight_nums))
                   + '</div>')
    digest_link = ('<span class="bf-sep">·</span>'
                   '<a class="dive-link" href="#digest">② 分段速览（各段一行）</a>') if has_digest else ""
    out.append(f'<div class="brief-foot">'
               f'<a class="dive-link bf-skip" href="{library_anchor}">跳过摘要，看全库内容 ↓</a>'
               f'{digest_link}</div>')
    out.append('</div></details>')
    return "\n".join(out)


def render_digest(rows, seg_meta, insights_md, mother, has_strategy):
    """② 总结层 v2.3.8「分段速览」：每段一行卡（段号+标题+## 摘要+「展开该段」），
    全部条目锚点下潜③层对应段；母题/洞察卡胶囊/战略诊断链接保留——
    摘要层忠实性问题（漏关键信息）的解药是可抽查。
    v2.3.1：②层存在时收编 overview 职能（母题索引），每个信息只出现在一层。
    v2.3.8：待办/风险表移入①摘要卡（每信息只出现在一层）。"""
    out = ['<h2 class="seg-title">② 分段速览</h2>',
           '<p class="seg-subtitle">各段摘要一行一段 · 点击任意条目展开该段 · 3 分钟读完</p>']
    if mother:
        out.append(f'<div class="card"><h3>母题</h3><p>{B.inline_fmt(mother)}</p></div>')
    if rows:
        out.append('<div class="card"><ol class="seg-quick">')
        for i in sorted(rows):
            title = seg_meta.get(i, (f"第{i}段", ""))[0]
            out.append(
                f'<li class="sq-row">'
                f'<a class="sq-num" href="#seg{i}" aria-label="第{i}段">{i}</a>'
                f'<div class="sq-body"><a class="sq-title" href="#seg{i}">{B.inline_fmt(title)}</a>'
                f'<p class="sq-sum">{B.inline_fmt(rows[i])}</p></div>'
                f'<a class="sq-open" href="#seg{i}">展开该段 ↓</a></li>')
        out.append('</ol></div>')
    cards = re.findall(r"^##\s+卡\s*(\d+)\s*[·•]?\s*(.+)$", insights_md, re.M) if insights_md else []
    if cards:
        out.append('<div class="card"><h3>核心洞察</h3><div class="digest-insights">')
        for num, name in cards:
            out.append(f'<a class="dive-link" href="#insight-{num}">卡{num} · {B.esc(name.strip())}</a>')
        out.append('</div></div>')
    if has_strategy:
        out.append('<div class="card"><p>战略诊断与行动清单：'
                   '<a class="dive-link" href="#strategy">下潜 →</a></p></div>')
    return "\n".join(out)


READ_PROTOCOL = (
    '<div class="read-protocol"><b>三层阅读</b>'
    '<span class="rp-tip">按需下潜：读完摘要即可走，有意思再往下点——省的是你的大脑</span>'
    '<span>① <a class="dive-link" href="#brief">执行摘要</a>（10 秒，一张卡）</span>'
    '<span>② <a class="dive-link" href="#digest">分段速览</a>（3 分钟，条目可下潜）</span>'
    '<span>③ 完整模块（左侧导航，按需查证）</span></div>'
)


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
            parts.append('<div class="card overview-card"><h3>人物</h3><ul class="people-quick">')
            for p in people:
                # 0% = 被提及未发言，不显示空百分比（2026-08-19 缺陷 6）
                tail = f'（约 {p["ratio"]}%）' if p["ratio"] else "（被提及）"
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
    speakers = [p for p in people if p["ratio"] > 0]
    mentioned = len(people) - len(speakers)
    # 口径修正（2026-08-19 缺陷 6）：05 人物卡含"被提及未发言者"，
    # 旧版一律计为"发言者"且给空进度条 + "约 ?%"
    if mentioned:
        sub = f'{len(speakers)} 位发言者 + {mentioned} 位被提及 · 头像 / 发言量'
    else:
        sub = f'{len(people)} 位发言者 · 头像 / 发言量'
    out = ['<h2 class="seg-title">人物角色卡</h2>',
           f'<p class="seg-subtitle">{sub}</p>']
    out.append('<div class="people-grid">')
    for p in people:
        # 卡片=视觉速览层（头像/名/发言量）；tagline 删除——它是下方折叠详情
        # 「背景与立场」首句的原文重复，每个信息只出现在一层
        head = (
            f'<div class="card people-card"><div class="people-head">'
            f'<div class="avatar" style="background:{p["color"]}">{B.esc(p["initial"])}</div>'
            f'<div class="people-meta"><div class="people-name">{B.esc(p["name"])}</div></div></div>')
        if p["ratio"] > 0:
            head += (
                f'<div class="people-bar-wrap"><div class="people-bar-label">发言量 约 {p["ratio"]}%</div>'
                f'<div class="people-bar-track"><div class="people-bar" style="width:{p["ratio"]}%;background:{p["color"]}"></div></div>'
                f'</div>')
        else:
            head += ('<div class="people-bar-wrap"><div class="people-bar-label">'
                     '被提及 · 未发言</div></div>')
        out.append(head + '</div>')
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


def build_sidebar(brand, seg_meta, counts, has_strategy, has_brief=False, has_digest=False,
                  show_overview=True):
    nav = []
    if has_brief:
        nav.append('<a href="#brief">① 执行摘要</a>')
    if show_overview:
        nav.append('<a href="#overview">总览</a>')
    if has_digest:
        nav.append('<a href="#digest">② 分段速览</a>')
    nav += [f'<a href="#people">人物角色卡（{counts["people"]} 人）</a>',
            '<a href="#map">议题关联地图</a>',
            f'<a href="#insights">洞察卡片（{counts["insights"]} 张）</a>',
            f'<a href="#method">方法论清单（{counts["method"]} 卡）</a>']
    if has_strategy:
        nav.append('<a href="#strategy">战略诊断与行动清单</a>')
    nav.append(f'<a href="#glossary">术语表（{counts["glossary"]} 条）</a>')
    nav.append('<a href="#data">关键数据速查</a>')
    if seg_meta:
        nav.append('<div class="nav-group"><div class="nav-group-title">主题分段（全文层）</div>')
        for i in sorted(seg_meta):
            t = seg_meta[i][0]
            short = t.split("·", 1)[-1].strip() if "·" in t else t
            nav.append(f'<a href="#seg{i}">{B.inline_fmt(short)}</a>')
        nav.append('</div>')
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
    insights_md = rd("08_洞察卡片.md")
    # v2.3.8 三层阅读 v2：①摘要卡（00_执行摘要全 BLUF）②分段速览（各段 ## 摘要）
    exec_md = rd("00_执行摘要.md")
    has_brief = bool(exec_md)
    rows = seg_digest_rows(seg_dir, seg_meta)
    has_digest = has_brief and bool(rows or mother)
    insight_nums = set(re.findall(r"^##\s+卡\s*(\d+)", insights_md, re.M))
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

    # 组装 sections（v2.3.1：有②层时自动 overview 收编——母题/人物索引并入②层，
    # 分段目录被②层各段要点取代（超集），导航卡被顶部协议横幅取代；
    # 定制总览（00_总览.md）与无②层的老场不受影响）
    show_overview = bool(overview_md) or not has_digest
    # 「跳过摘要，看全库内容 ↓」锚到③层首个实际渲染模块（定制总览优先）
    lib_first = "overview" if show_overview else next(
        (sid for sid, has in (("people", people_md), ("map", rd("07_议题关联地图.md")),
                              ("insights", insights_md), ("method", rd("03_方法论清单.md")),
                              ("strategy", has_strategy), ("glossary", rd("04_术语表.md")),
                              ("data", rd("06_关键数据速查.md"))) if has), "seg1")
    library_anchor = f"#{lib_first}"
    sections = []
    if has_brief:
        sections.append('    <section id="brief">\n'
                        + render_brief(exec_md, [p["name"] for p in people], insight_nums,
                                       library_anchor, has_digest) + '\n    </section>')
    if show_overview:
        sections.append('    <section id="overview">\n' + B.render_overview() + '\n    </section>')
    if has_digest:
        sections.append('    <section id="digest">\n'
                        + render_digest(rows, seg_meta, insights_md, mother, has_strategy)
                        + '\n    </section>')
    if people_md:
        sections.append('    <section id="people">\n' + B.render_people(people_md) + '\n    </section>')
    if rd("07_议题关联地图.md"):
        sections.append('    <section id="map">\n' + B.render_map(rd("07_议题关联地图.md")) + '\n    </section>')
    if rd("08_洞察卡片.md"):
        sections.append('    <section id="insights">\n' + B.render_insights(rd("08_洞察卡片.md")) + '\n    </section>')
    if rd("03_方法论清单.md"):
        sections.append('    <section id="method">\n' + B.render_method(rd("03_方法论清单.md")) + '\n    </section>')
    if has_strategy:
        sections.append('    <section id="strategy">\n<h2 class="seg-title">战略诊断与行动清单</h2>'
                        '<p class="seg-subtitle">现状 → 定位 → 路径 → 行动</p>\n'
                        + render_md_with_code(strip_h1(rd("09_战略诊断与行动清单.md")), sortable=True) + '\n    </section>')
    if rd("04_术语表.md"):
        sections.append('    <section id="glossary">\n' + B.render_glossary(rd("04_术语表.md")) + '\n    </section>')
    if rd("06_关键数据速查.md"):
        sections.append('    <section id="data">\n' + B.render_data(rd("06_关键数据速查.md")) + '\n    </section>')
    # 主题分段=全文层，垫底（v2.3.2：模块在前、16 段详情在末，按需查证）
    if seg_dir.exists():
        seen_asides = set()
        for sf in sorted(seg_dir.glob("第*段_*.md"),
                         key=lambda p: int(re.search(r"第(\d+)段", p.name).group(1))):
            i = int(re.search(r"第(\d+)段", sf.name).group(1))
            seg_md = dedupe_asides(sf.read_text(encoding="utf-8"), seen_asides)
            sections.append(f'    <section id="seg{i}">\n' + B.render_seg(i, seg_md) + '\n    </section>')

    tpl = B.TEMPLATE.replace("    <!--SECTIONS-->", "\n\n".join(sections))
    sidebar = build_sidebar(brand, seg_meta, counts, has_strategy, has_brief, has_digest, show_overview)
    html_out = re.sub(r'<aside class="sidebar".*?</aside>', sidebar, tpl, count=1, flags=re.S)
    # v2.3 阅读协议横幅插在 main 顶部（有①层才提示三层协议；轻档场不打扰）
    if has_brief:
        html_out = re.sub(r"(<main[^>]*>)",
                          lambda m: m.group(1) + "\n    " + READ_PROTOCOL,
                          html_out, count=1)
    # 修母版里写死首场的标题/副标题
    html_out = html_out.replace("<title>聊聊AI工业应用 · 全场整理</title>",
                                f"<title>{brand} · 全场整理</title>")
    # 母版首场标题固定化（目录名硬拼进标题曾是 bug：显示全路径名）
    html_out = html_out.replace("B 方法论清单", "方法论清单")
    html_out = html_out.replace("14 张可复用的思维工具卡 · 定义 + 出处 + 怎么用",
                                "方法论卡 · 定义 + 出处 + 怎么用")

    # v2.3.7 起输出文件名=场次目录名（用户 2026-09-06 要求：index.html 无辨识度，浏览器标签/搜索分不清场次）
    out_path = pack_dir / f"{pack_dir.name}.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"✓ 已生成 {out_path}（{out_path.stat().st_size / 1024:.1f} KB）")
    print(f"  段:{len(seg_meta)} 人:{counts['people']} 洞察:{counts['insights']} "
          f"方法论:{counts['method']} 术语:{counts['glossary']} 战略诊断:{'有' if has_strategy else '无'}")

    # ---- 渲染质量自检（2026-08-19 六类缺陷的回归护栏）----
    problems = []
    # 1) 副标题泄漏未消化的 markdown（`**` 字面出现）
    n_star = len(re.findall(r'class="seg-subtitle">[^<]*\*\*', html_out))
    if n_star:
        problems.append(f"seg-subtitle 含未消化 markdown 星号 ×{n_star}")
    # 2) 旧对比度问题色残留（先剥 CSS 注释，避免注释里的历史色值说明误报）
    css_stripped = re.sub(r"/\*.*?\*/", "", html_out, flags=re.S)
    n_old = len(re.findall(r"#00b894|#e8910a", css_stripped))
    if n_old:
        problems.append(f"旧低对比色 #00b894/#e8910a 残留 ×{n_old}")
    # 3) 死 CSS 类是否复活（正文不应出现 map-chip/databar）
    n_dead = len(re.findall(r'class="[^"]*(?:map-chip|databar)', html_out))
    if n_dead:
        problems.append(f"死类 map-chip/databar 出现在正文 ×{n_dead}")
    # 4) 重复映射注（去重后同类注释文本不应再多次出现）。
    #    blockquote 需剥内联标签后比对（`> **注**：` 渲染含 <strong>）
    note_texts = re.findall(r'class="aside-tag">\[[^\]]+\]</span> ([^<]+)', html_out)
    for bq in re.findall(r"<blockquote>(.*?)</blockquote>", html_out, flags=re.S):
        t = re.sub(r"<[^>]+>", "", bq).strip()
        if t.startswith(("注", "说明", "备注", "说话人映射", "**注**")):
            note_texts.append(t)
    dup = {t.strip() for t in note_texts if len(t) > 10 and note_texts.count(t) > 1}
    if dup:
        problems.append(f"逐字重复的注释行仍存在（段间应由渲染器去重，"
                        f"模块间的请只写在 05 人物卡头部）：{'; '.join(list(dup)[:2])}")
    if problems:
        print("⚠ 渲染质量自检发现问题：")
        for p in problems:
            print(f"  - {p}")
    else:
        print("✓ 渲染质量自检通过（副标题/对比色/死类/重复注/锚点/收敛）")
    # ---- v2.3 三层收敛检查 ----
    ids = set(re.findall(r'id="([\w-]+)"', html_out))
    bad_anchors = sorted({a for a in re.findall(r'href="#([\w-]+)"', html_out) if a not in ids})
    if bad_anchors:
        print(f"⚠ 死锚点（href 目标不存在）：{', '.join(bad_anchors[:6])}")
    else:
        n_links = len(re.findall(r'class="dive-link', html_out))
        print(f"✓ 锚点全部有效（下潜链接 {n_links} 处）")
    m_dg = re.search(r'<section id="digest">(.*?)</section>', html_out, re.S)
    if m_dg:
        # 阅读量统计：剥卡胶囊与「展开该段」控件（点选≠阅读）
        core = re.sub(r'<a class="sq-open"[^>]*>.*?</a>'
                      r"|<div class=\"digest-insights\">.*?</div>", "", m_dg.group(1), flags=re.S)
        t = re.sub(r"<[^>]+>", "", core)
        n_chars = len(re.sub(r"\s", "", t))
        # 阈值随段数弹性：常规 6-10 段压 ~1000 字内；重装场每行 ~130 字预算
        # （v2.3.8 行=段号+段标题+## 摘要句(≤100)，较 v2.3 段结论首句(~60)宽）
        limit = max(1200, len(rows) * 130)
        flag = "⚠ 超字数规格" if n_chars > limit else "✓"
        print(f"{flag} ② 分段速览阅读量 {n_chars} 字（限额 {limit}，速览行 {len(rows)} 条；控件/卡胶囊不计）")
    if not has_brief and seg_dir.exists():
        print("⚠ 缺 00_执行摘要.md——①简报层不成立（v2.3 起标准/重装档必写）")


if __name__ == "__main__":
    main()
