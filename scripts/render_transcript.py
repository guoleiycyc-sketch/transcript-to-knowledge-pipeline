#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_transcript.py —— 清洗稿外发 HTML 渲染器

把 <场次目录>/01_清洗稿.md 渲染为可外发客户的版式：
  HTML：<场次目录>/<场次目录名>_清洗稿.html（命名与场次知识包 HTML 同规范，不用 index.html）
  MD  ：<场次目录>/<场次目录名>_清洗稿.md（纯 Markdown 文档版，微信/协作工具直发，2026-09-16 用户需求）

外发版内容策略（2026-09-16 用户需求）：
  - 保留：正文章节 + 逐回合对话（**【人名】** [ts] 正文）+ 附录 B 金句候选
  - 剔除：头部技术块（来源块/说话人映射/清洗原则/ASR 对照表）与附录 A/C/D
    （映射与存疑分析属教练团内部信息，不外发）
  - 参与人列表：从正文回合人名自动统计

用法：python3 render_transcript.py <场次目录> [--format html|md] [--out 自定义输出路径]
幂等：重跑覆盖。"""
import argparse, html, os, re, sys
from collections import Counter

HEAD_SKIP = re.compile(r'^(来源|一、来源|.*说话人映射|.*清洗原则|.*ASR.*对照表)')
APPX_B = re.compile(r'^附录\s*B')
APPX_ANY = re.compile(r'^附录')
TURN = re.compile(r'^\*\*【([^】]+)】\*\* \[(\d{2}:\d{2}:\d{2})\]\s*(.*)$')

# 外发显示层人名映射（2026-09-16 用户规范：正式文件用全名；仅改 HTML 显示，不动 md 校验锚）
def display_name(who):
    for k, v in {'B〔ASR存疑〕': 'B', 'B': 'B', 'B': 'B',
                 'D': 'D'}.items():
        if k in who:
            return who.replace(k, v)
    return who

CSS = """
:root{--ink:#1a2332;--ink2:#4a5568;--ink3:#718096;--accent:#0e7490;--accent2:#155e75;
--bg:#f7fafc;--card:#fff;--line:#e2e8f0;--tag-bg:#e0f2fe;--tag-ink:#0369a1;--gold:#b45309;--gold-bg:#fffbeb}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
color:var(--ink);background:var(--bg);line-height:1.8;font-size:15px}
.wrap{max-width:860px;margin:0 auto;padding:44px 26px 60px}
header.hero{background:linear-gradient(135deg,#0e7490,#155e75 60%,#1e3a5f);color:#fff;border-radius:16px;
padding:34px 38px 28px;box-shadow:0 10px 30px rgba(14,116,144,.18)}
.kicker{font-size:12px;letter-spacing:.35em;opacity:.85;margin-bottom:8px}
h1{font-size:24px;font-weight:700;margin-bottom:6px}
.meta{display:flex;flex-wrap:wrap;gap:8px 24px;margin-top:14px;font-size:13px;opacity:.95}
.meta i{font-style:normal;opacity:.7;margin-right:4px}
nav.toc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 22px;margin-top:20px}
nav.toc b{font-size:13px;color:var(--accent2);letter-spacing:.1em}
nav.toc a{display:block;font-size:13.5px;color:var(--ink2);text-decoration:none;padding:2.5px 0}
nav.toc a:hover{color:var(--accent)}
section{margin-top:34px}
h2.sec{font-size:18px;font-weight:700;color:var(--accent2);border-left:4px solid var(--accent);padding-left:12px;margin-bottom:4px}
.sec-sub{font-size:12.5px;color:var(--ink3);margin-bottom:14px;padding-left:16px}
.t{display:flex;gap:12px;padding:9px 0;border-top:1px dashed var(--line);page-break-inside:avoid}
.turns .t:first-child{border-top:none}
.t .who{flex:none;width:92px;font-weight:700;color:var(--accent2);font-size:14px}
.t .who.me{color:var(--gold)}
.t .body{flex:1}
.t .ts{font-size:11.5px;color:var(--ink3);font-variant-numeric:tabular-nums;margin-right:6px}
.note{font-size:13px;color:var(--ink3);padding:2px 0 2px 104px}
.q{margin-top:26px;background:var(--gold-bg);border:1px solid #fde68a;border-radius:12px;padding:16px 22px}
.q b{font-size:13px;color:#92400e;letter-spacing:.1em}
.q li{list-style:none;font-size:14px;color:#78350f;padding:4px 0}
footer{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);color:var(--ink3);font-size:12.5px;
display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
@media print{body{background:#fff}.wrap{padding:0}header.hero{border-radius:0}}
"""

def render(dirpath, out=None, fmt="html"):
    src = os.path.join(dirpath, '01_清洗稿.md')
    if not os.path.exists(src):
        sys.exit(f'未找到 {src}')
    lines = open(src).read().split('\n')
    dirname = os.path.basename(os.path.normpath(dirpath))
    m = re.search(r'(\d{4}-\d{2}-\d{2})', dirname)
    date = m.group(1) if m else ''
    title = dirname
    for l in lines[:5]:
        if l.startswith('# '):
            title = re.sub(r'\s*[·—-]?\s*清洗稿\s*$', '', l[2:].strip()); break

    sections, people = [], Counter()
    state = 'skip'  # skip|sec|appx_b|appx_other
    cur = None
    for l in lines:
        mh = re.match(r'^(#{2,3}) (.+)$', l)
        if mh:
            h = mh.group(2).strip()
            if APPX_ANY.match(h):
                state = 'appx_b' if APPX_B.match(h) else 'appx_other'
                cur = {'kind': 'appx_b', 'title': h, 'items': []} if state == 'appx_b' else None
                if cur: sections.append(cur)
            elif HEAD_SKIP.match(h) or h == '逐字稿' or h == '称呼说明':
                state = 'skip'; cur = None
            else:
                state = 'sec'
                cur = {'kind': 'sec', 'title': h, 'items': []}
                sections.append(cur)
            continue
        if not l.strip() or cur is None:
            continue
        if state == 'sec':
            mt = TURN.match(l)
            if mt:
                who, ts, body = mt.groups()
                people[who] += 1
                cur['items'].append(('turn', who, ts, body))
            else:
                cur['items'].append(('text', l.strip()))
        elif state == 'appx_b':
            cur['items'].append(('text', l.strip()))

    p = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="wrap">']
    pl = ' · '.join(f'{display_name(k)}（{v}）' for k, v in people.most_common())
    p.append(f'<header class="hero"><div class="kicker">TRANSCRIPT · 逐字稿</div><h1>{html.escape(title)}</h1>'
             f'<div class="meta"><span><i>日期</i>{date}</span></div>'
             f'<div class="meta" style="margin-top:6px"><span><i>发言（回合数）</i>{html.escape(pl)}</span></div></header>')
    secs = [s for s in sections if s['kind'] == 'sec']
    p.append('<nav class="toc"><b>目录</b>')
    for i, s in enumerate(secs, 1):
        p.append(f'<a href="#s{i}">{html.escape(s["title"])}</a>')
    p.append('</nav>')
    for i, s in enumerate(secs, 1):
        p.append(f'<section id="s{i}"><h2 class="sec">{html.escape(s["title"])}</h2><div class="turns">')
        for item in s['items']:
            if item[0] == 'text':
                t = html.escape(item[1].lstrip('> '))
                if t: p.append(f'<div class="note">{t}</div>')
            else:
                _, who, ts, body = item
                who_d = display_name(who)
                cls = 'who me' if 'F' in who else 'who'
                p.append(f'<div class="t"><div class="{cls}">{html.escape(who_d)}</div><div class="body">'
                         f'<span class="ts">[{ts}]</span>{html.escape(body)}</div></div>')
        p.append('</div></section>')
    for s in sections:
        if s['kind'] == 'appx_b' and s['items']:
            p.append('<div class="q"><b>金句摘录</b><ul>')
            for item in s['items']:
                t = html.escape(item[1].lstrip('>- ').strip())
                if t: p.append(f'<li>{t}</li>')
            p.append('</ul></div>')
    p.append(f'<footer><span>本逐字稿基于 {date} 现场录音整理 · 仅供参会方留存，请勿转发</span>'
             f'<span>教练团 整理</span></footer></div></body></html>')

    out = out or os.path.join(dirpath, f'{dirname}_清洗稿.{fmt}')
    open(out, 'w').write('\n'.join(p))
    print(f'✓ 已生成 {out}（{sum(people.values())} 回合，{len(secs)} 节，参与：{pl}）')


def render_md(dirpath, out=None):
    """MD 外发版：与 HTML 版同内容策略的纯 Markdown 文档"""
    src = os.path.join(dirpath, '01_清洗稿.md')
    if not os.path.exists(src):
        sys.exit(f'未找到 {src}')
    lines = open(src).read().split('\n')
    dirname = os.path.basename(os.path.normpath(dirpath))
    m = re.search(r'(\d{4}-\d{2}-\d{2})', dirname)
    date = m.group(1) if m else ''
    title = dirname
    for l in lines[:5]:
        if l.startswith('# '):
            title = re.sub(r'\s*[·—-]?\s*清洗稿\s*$', '', l[2:].strip()); break

    sections, people = [], Counter()
    state, cur = 'skip', None
    for l in lines:
        mh = re.match(r'^(#{2,3}) (.+)$', l)
        if mh:
            h = mh.group(2).strip()
            if APPX_ANY.match(h):
                state = 'appx_b' if APPX_B.match(h) else 'appx_other'
                cur = {'kind': 'appx_b', 'items': []} if state == 'appx_b' else None
                if cur: sections.append(cur)
            elif HEAD_SKIP.match(h) or h in ('逐字稿', '称呼说明'):
                state = 'skip'; cur = None
            else:
                state = 'sec'; cur = {'kind': 'sec', 'title': h, 'items': []}
                sections.append(cur)
            continue
        if not l.strip() or cur is None:
            continue
        if state == 'sec':
            mt = TURN.match(l)
            if mt:
                who, ts, body = mt.groups()
                people[who] += 1
                cur['items'].append(('turn', who, ts, body))
            elif not l.startswith('## '):
                cur['items'].append(('text', l.strip()))
        elif state == 'appx_b':
            cur['items'].append(('text', l.strip()))

    p = [f'# {title} · 逐字稿（外发版）', '',
         f'> {date} · 发言（回合数）：' + ' · '.join(f'{display_name(k)}（{v}）' for k, v in people.most_common()),
         '> 仅供参会方留存，请勿转发', '']
    secs = [s for s in sections if s['kind'] == 'sec']
    for s in secs:
        p.append(f'## {s["title"]}')
        p.append('')
        for item in s['items']:
            if item[0] == 'text':
                t = item[1].lstrip('> ')
                if t: p.append(f'> {t}'); p.append('')
            else:
                _, who, ts, body = item
                p.append(f'**【{display_name(who)}】** [{ts}] {body}')
                p.append('')
    for s in sections:
        if s['kind'] == 'appx_b' and s['items']:
            p.append('## 金句摘录')
            p.append('')
            for item in s['items']:
                t = item[1].lstrip('>- ').strip()
                if t: p.append(f'- {t}')
            p.append('')
    p.append('---')
    p.append(f'*本逐字稿基于 {date} 现场录音整理 · 教练团 整理*')
    out = out or os.path.join(dirpath, f'{dirname}_清洗稿.md')
    open(out, 'w').write('\n'.join(p) + '\n')
    pl = ' · '.join(f'{display_name(k)}（{v}）' for k, v in people.most_common())
    print(f'✓ 已生成 {out}（{sum(people.values())} 回合，{len(secs)} 节，参与：{pl}）')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('dirpath'); ap.add_argument('--out'); ap.add_argument('--format', default='html', choices=['html', 'md'])
    a = ap.parse_args()
    if a.format == 'md':
        render_md(a.dirpath, a.out)
    else:
        render(a.dirpath, a.out)
