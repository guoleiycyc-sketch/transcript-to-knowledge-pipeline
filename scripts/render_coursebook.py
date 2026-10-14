#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""培训讲义双渲器：10_培训讲义/（course_map.json + 第N课_*.md）→ 讲师版 / 学员版单文件 HTML。

用法: python3 render_coursebook.py <培训讲义目录>
  讲师版 <课程名>_讲师版.html：:::coach 讲师提示卡、时戳全保留、【标注】chip、侧栏课时导航、课程信息卡
  学员版 <课程名>_学员版.html：coach 块/时戳/标注剔除、脱敏（客户名/金额/王翠段）、粗口替换、A4 打印友好
  红线闸：课时 md 命中 course_map.excluded_from_all_versions 标记（时戳/关键词）→ 拒绝渲染退出 1
  URL ?course=N 投屏聚焦（JS 切换显示；默认全显 + 侧栏导航）

Safety: Python stdlib only；只读讲义目录，只写两个 HTML 回同目录。
"""
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_html as B  # noqa: E402  复用 esc/inline_fmt/md_to_blocks/render_blocks_generic

TS_RE = re.compile(r"\[\d{1,3}:\d{2}(?::\d{2})?\]")
COACH_SPLIT = re.compile(r"(:::coach\b.*?:::)", re.S)
SENT_SPLIT = re.compile(r"(?<=[。！？；\n])")

# 学员版脱敏映射（初版硬编码，对应 course_map.desensitize_in_student_version；按需扩充）
# 脱敏映射：默认空（通用）。业务方在 course_map.json 的 desensitize_in_student_version
# 给出 name_map 时生效——脱敏对象是「对受训员工不适暴露的外部信息」（外部客户名/金额），
# 受训方自身的老板与公司名属教学语境，默认不脱。
NAME_MAP = {}
PROFANITY = [("他妈的", ""), ("他妈", ""), ("牛逼", "厉害"), ("我靠", "天")]
WANGCUI_REPL = "（有团队在试验新的版本管理工具）"

CSS = """
body{font-family:"PingFang SC",system-ui,sans-serif;margin:0;background:#fafaf8;color:#1f2937;line-height:1.85}
.sidebar{position:fixed;left:0;top:0;bottom:0;width:232px;background:#f3f1ea;border-right:1px solid #e5e2da;
padding:18px 14px;overflow-y:auto;box-sizing:border-box}
.side-title{font-size:12px;color:#8b8578;letter-spacing:.08em;margin-bottom:10px}
.sidebar a,.nav-miss{display:block;padding:6px 10px;border-radius:6px;font-size:13px;color:#1f2937;
text-decoration:none;margin-bottom:2px}
.sidebar a:hover{background:#e9e5da}
.sidebar .dur{color:#8b8578;font-size:11px}
.nav-miss{color:#b3ac9d}
main{margin-left:232px;padding:28px 40px 40px;max-width:920px}
.info-card{background:#fff;border:1px solid #e5e2da;border-radius:10px;padding:16px 22px;margin-bottom:26px;font-size:13.5px}
.info-card h1{font-size:20px;margin:0 0 6px}
.info-card .ver{color:#8b8578;font-size:12px}
.info-dec{margin-top:8px;border-top:1px dashed #e5e2da;padding-top:8px;font-size:12.5px;color:#57534e}
.course-sec{background:#fff;border:1px solid #e5e2da;border-radius:10px;padding:24px 30px;margin-bottom:30px}
.course-sec h1{font-size:19px;border-bottom:2px solid #2b62d6;padding-bottom:8px;margin:0 0 4px}
.course-sec h2{font-size:16.5px;margin:22px 0 8px}
.course-sec h3{font-size:15px;margin:18px 0 6px}
.course-sec h4{font-size:13.5px;margin:14px 0 4px;color:#57534e}
.cmeta{font-size:12px;color:#8b8578;margin:0 0 14px}
p{margin:8px 0} ul,ol{padding-left:1.6em;margin:8px 0} li{margin:3px 0}
hr.soft{border:none;border-top:1px dashed #e5e2da;margin:16px 0}
.coach{background:#fff8e6;border:1px solid #f0d896;border-left:4px solid #d4a72c;border-radius:8px;
padding:12px 18px;margin:14px 0}
.coach-h{font-size:12px;font-weight:700;color:#8a6d1a;letter-spacing:.06em;margin-bottom:6px}
.ts{font-size:11px;color:#a8a294;font-family:ui-monospace,Menlo,monospace}
.mk{font-size:11.5px;font-weight:700;border-radius:4px;padding:1px 6px;white-space:nowrap}
.mk0{background:#fee2e2;color:#b91c1c}.mk1{background:#fef3c7;color:#92400e}
.mk2{background:#dbeafe;color:#1d4ed8}.mk3{background:#f3e8ff;color:#6d28d9}
.mk4{background:#dcfce7;color:#15803d}.mk5{background:#ffedd5;color:#c2410c}
.mk6{background:#e0f2fe;color:#0369a1}.mk7{background:#f1f5f9;color:#334155}
blockquote{border-left:3px solid #cbb;border-radius:0 6px 6px 0;background:#faf9f4;padding:2px 14px;margin:10px 0}
.md-table{border-collapse:collapse;margin:10px 0;font-size:13px}
.md-table th,.md-table td{border:1px solid #e5e2da;padding:5px 10px}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:.92em;background:#f2f0e9;border-radius:3px;padding:0 4px}
pre.ascii-map{background:#1f2937;color:#e5e7eb;padding:12px 16px;border-radius:8px;overflow-x:auto;font-size:12px;line-height:1.5}
.page-foot{text-align:center;color:#8b8578;font-size:12px;margin:30px 0 10px}
.focus-mode .sidebar{display:none}
.focus-mode main{margin-left:0}
@media print{
 body{background:#fff;font-size:10.5pt}
 .sidebar{display:none} main{margin:0;padding:0;max-width:none}
 .course-sec{border:none;border-radius:0;padding:0;padding-right:25%;page-break-before:always}
 .course-sec:first-of-type{page-break-before:avoid}
 .info-card{border:none;background:#fff}
 .page-foot{page-break-inside:avoid}
}
@page{size:A4;margin:18mm 16mm}
"""

JS = """
(function(){
 function show(n){
  var secs=document.querySelectorAll('.course-sec');
  document.body.classList.toggle('focus-mode',!!n);
  var hit=false;
  secs.forEach(function(s){var on=s.getAttribute('data-course')===n;s.style.display=on?'':'none';if(on)hit=true});
  if(n&&!hit){secs.forEach(function(s){s.style.display=''}) ;document.body.classList.remove('focus-mode')}
 }
 var m=location.search.match(/[?&]course=(\\d+)/);
 if(m)show(m[1]);
 document.querySelectorAll('.sidebar a[data-course]').forEach(function(a){
  a.addEventListener('click',function(){show(a.getAttribute('data-course'))});
 });
})();
"""


def redline_markers(items):
    """excluded_from_all_versions 条目 → 红线标记集（行内时戳 + 去 §/括注后 ≥4 汉字的关键段）。"""
    marks = set()
    for it in items:
        s = re.sub(r"（[^）]*）|\([^)]*\)", "", str(it))
        marks.update(TS_RE.findall(s))
        for seg in re.split(r"[·,，;；/、]", s):
            if len(re.sub(r"[^一-鿿]", "", seg)) >= 4:
                marks.add(seg.strip())
    return marks


def student_md(md, marks):
    """学员版源文变换：标注/时戳剔除 + 脱敏 + 粗口（coach 块在 lesson_html 切块时丢弃）。"""
    for m in marks:
        md = md.replace(f"【{m}】", "")
    md = TS_RE.sub("", md)
    for a, b in NAME_MAP.items():
        md = md.replace(a, b)
    md = re.sub(r"(?:\d+(?:\.\d+)?|[一二两三四五六七八九十百零]+)(?=\s*万)", "X", md)  # 金额→X万（阿拉伯/中文数字，保留「万」）
    md = "".join(WANGCUI_REPL if "王翠" in s else s for s in SENT_SPLIT.split(md))
    for a, b in PROFANITY:
        md = md.replace(a, b)
    return md


def lesson_html(md, student, marks):
    """一课 md → HTML：:::coach 块抽离（讲师=提示卡 / 学员=剔除），其余走母版块渲染。"""
    md = re.sub(r"^#\s+.+\n+", "", md, count=1)  # 课时大标题由外层 section h1 承担
    out = []
    for piece in COACH_SPLIT.split(md):
        if piece.startswith(":::coach"):
            if student:
                continue
            lines = piece.strip().split("\n")
            inner = "\n".join(lines[1:-1]).strip() if len(lines) > 2 else ""
            body = B.render_blocks_generic(B.md_to_blocks(inner))
            out.append('<div class="coach"><div class="coach-h">💡 讲师提示</div>'
                       + body + "</div>")
        elif piece.strip():
            html = B.render_blocks_generic(B.md_to_blocks(piece))
            if not student:
                html = TS_RE.sub(lambda m: f'<span class="ts">{m.group(0)}</span>', html)
                for i, mk in enumerate(marks):
                    html = html.replace(f"【{mk}】", f'<span class="mk mk{i % 8}">【{mk}】</span>')
            out.append(html)
    return "\n".join(out)


def page_html(cmap, nav, secs, student):
    """组装整页：侧栏导航 + 信息卡 + 课时 section + 页脚（学员版含脱敏声明）。"""
    course, ver = cmap.get("course", "培训讲义"), cmap.get("version", "")
    variant = "学员版" if student else "讲师版"
    if student:
        info = (f'<h1>{B.esc(course)}</h1><p class="ver">{B.esc(ver)} · 学员版</p>'
                f'<p class="ver">{B.esc(cmap.get("audience_baseline", ""))}</p>')
        foot = (f"学员版·已脱敏 {B.esc(ver)}｜口语已按学员版规范替换"
                if ver else "学员版·已脱敏｜口语已按学员版规范替换")
    else:
        dec = "".join(f'<div><b>{B.esc(k)}</b>：{B.inline_fmt(str(v))}</div>'
                      for k, v in cmap.get("decision_log", {}).items())
        info = (f'<h1>{B.esc(course)}</h1><p class="ver">{B.esc(ver)} · 讲师版 · '
                f'受众基线：{B.esc(cmap.get("audience_baseline", ""))}</p>'
                f'<div class="info-dec"><b>决策记录</b>{dec}</div>')
        foot = f"讲师版 · 内部使用 · {B.esc(ver)}"
    nav_html = '<div class="side-title">课时导航</div><a data-course="" href="#">全部课时</a>'
    for n in nav:
        label = f'第{n["id"]}课 {B.esc(n["title"])} <span class="dur">{B.esc(n["meta"])}</span>'
        if n["has"]:
            nav_html += f'<a data-course="{n["id"]}" href="#course-{n["id"]}">{label}</a>'
        else:
            nav_html += f'<span class="nav-miss">{label} ·未产出</span>'
    return ("<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{B.esc(course)} · {variant}</title><style>{CSS}</style></head><body>"
            f'<aside class="sidebar">{nav_html}</aside>'
            f'<main><header class="info-card">{info}</header>{"".join(secs)}'
            f'<footer class="page-foot">{B.esc(foot)}</footer></main>'
            f"<script>{JS}</script></body></html>")


def main():
    if len(sys.argv) != 2:
        print("用法: python3 render_coursebook.py <培训讲义目录>"); sys.exit(1)
    d = Path(sys.argv[1]).resolve()
    cmap_p = d / "course_map.json"
    if not cmap_p.exists():
        print(f"[render_coursebook] 缺 course_map.json：{cmap_p}"); sys.exit(1)
    cmap = json.loads(cmap_p.read_text(encoding="utf-8"))
    marks = cmap.get("marks", [])

    files = {}
    for p in sorted(d.glob("*.md")):
        m = re.match(r"^第(\d+)课", p.stem)
        if m:
            files[int(m.group(1))] = p

    # 红线保险闸：任何课时 md 命中 excluded_from_all_versions 标记 → 拒绝渲染
    rl = redline_markers(cmap.get("excluded_from_all_versions", []))
    for cid, p in sorted(files.items()):
        hit = [x for x in rl if x in p.read_text(encoding="utf-8")]
        if hit:
            print(f"[红线闸] {p.name} 命中 excluded_from_all_versions 标记 {hit} → 拒绝渲染")
            sys.exit(1)

    secs_t, secs_s, nav, missing = [], [], [], []
    for c in cmap.get("courses", []):
        cid, title = c.get("id"), c.get("title", "")
        meta = " · ".join(str(x) for x in (c.get("duration", ""), c.get("status", ""),
                                           "/".join(c.get("sections", []))) if x)
        p = files.pop(cid, None)
        nav.append({"id": cid, "title": title, "meta": meta, "has": p is not None})
        if not p:
            missing.append(f"第{cid}课 {title}")
            continue
        raw = p.read_text(encoding="utf-8")
        head = (f'<section class="course-sec" id="course-{cid}" data-course="{cid}">'
                f'<h1>第{cid}课 · {B.esc(title)}</h1>'
                f'<p class="cmeta">{B.esc(nav[-1]["meta"])}</p>')
        secs_t.append(head + lesson_html(raw, False, marks) + "</section>")
        secs_s.append(head + lesson_html(student_md(raw, marks), True, marks) + "</section>")
    extras = []
    for cid, p in sorted(files.items()):  # 未登记进 course_map 的课时文件也渲上
        extras.append(p.name)
        head = (f'<section class="course-sec" id="course-{cid}" data-course="{cid}">'
                f'<h1>{B.esc(p.stem.replace("_", " "))}</h1>')
        raw = p.read_text(encoding="utf-8")
        secs_t.append(head + lesson_html(raw, False, marks) + "</section>")
        secs_s.append(head + lesson_html(student_md(raw, marks), True, marks) + "</section>")

    course = re.sub(r'[/\\:*?"<>|]', "", cmap.get("course", "培训讲义")).strip()
    outs = []
    for student, secs in ((False, secs_t), (True, secs_s)):
        out = d / f"{course}_{'学员版' if student else '讲师版'}.html"
        out.write_text(page_html(cmap, nav, secs, student), encoding="utf-8")
        outs.append(out)

    print(f"[render_coursebook] 课程：{cmap.get('course', '')}（{cmap.get('version', '')}）")
    print(f"  已渲染 {len(secs_t)} 课" + (f"；缺失跳过 {len(missing)} 课：{'；'.join(missing)}" if missing else ""))
    if extras:
        print(f"  ⚠️ 未登记课时文件（照渲）：{', '.join(extras)}")
    for o in outs:
        print(f"  输出：{o}")


if __name__ == "__main__":
    main()
