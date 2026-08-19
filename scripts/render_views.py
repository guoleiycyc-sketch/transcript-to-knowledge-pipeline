#!/usr/bin/env python3
"""render_views.py — 从 atoms.jsonl 生成视图（第三批：单库多视图的视图层）

用法：
  python3 render_views.py <录音项目根> --view methods     # 方法论总库视图（md，带出现场次计数）
  python3 render_views.py <录音项目根> --view quotes       # 引语库完整视图
  python3 render_views.py <录音项目根> --view quotes --max-sens N   # 脱敏：只留 N 级（N=普通 P=价格 H=健康）
  python3 render_views.py <录音项目根> --view share        # 脱敏分享版 HTML（过滤 P/H 级，自包含可发给团队/客户）
  python3 render_views.py <录音项目根> --view decisions    # 从决策日志 md 生成只读视图

设计依据：Zettelkasten "single source of truth + views as derived perspectives"——
原子唯一存在于 atoms.jsonl，本脚本生成一切派生视图；改原子重跑即可，不手改视图。
"""
import json, os, sys, html

ROOT = sys.argv[1]
VIEW = 'methods'
ARGS = sys.argv[2:]
if '--view' in ARGS:
    VIEW = ARGS[ARGS.index('--view') + 1]
MAX_SENS = 'P' if '--max-sens' not in ARGS else ARGS[ARGS.index('--max-sens') + 1]
SENS_ORDER = {'N': 0, 'P': 1, 'H': 2}

def load():
    p = os.path.join(ROOT, '_全局资产', 'atoms.jsonl')
    if not os.path.exists(p):
        print(f'未找到 {p}，先跑 extract_atoms.py'); sys.exit(1)
    return [json.loads(l) for l in open(p) if l.strip()]

# 同题归并规则（module 级，view_methods 与 view_share_html 共用）
RULES = [
    ('窗口期', ['窗口']), ('FDE', ['FDE']), ('上下文沉淀/三部曲', ['上下文', '三部曲', '沉淀']),
    ('免费分位论', ['免费', '六七十分']), ('定价/收钱', ['定价', '收钱', '成本切分', '价值', '谈钱', '预算内']),
    ('代练/做没了', ['代练', '做没']), ('样板', ['样板']), ('灯塔客户', ['灯塔']),
    ('改装车', ['改装车']), ('销讲', ['销讲']), ('WorkBuddy 分档', ['WorkBuddy', '精英逻辑', '分档']),
    ('数字分身', ['数字分身']), ('本体论数据', ['本体论', '本体层']), ('token', ['token']),
]

def view_methods(atoms):
    methods = [a for a in atoms if a['type'] == 'method']
    merged = {}
    for a in methods:
        key = next((k for k, kws in RULES if any(kw in a['title'] for kw in kws)), a['title'])
        merged.setdefault(key, []).append(a)
    lines = ['# 方法论总库 · 自动视图', '',
             f'> 由 atoms.jsonl 生成（{len(methods)} 条原子，归并 {len(merged)} 条）；出现场次 ≥3 = 销讲课模块候选', '']
    for k, v in sorted(merged.items(), key=lambda x: -len(set(a['session'] for a in x[1]))):
        sids = sorted(set(a['session'] for a in v))
        star = ' ⭐' if len(sids) >= 3 else ''
        lines.append(f'## {k}（{len(sids)} 场）{star}')
        for a in sorted(v, key=lambda x: x['session']):
            lines.append(f"- {a['session']}：{a['title']}")
        lines.append('')
    return '\n'.join(lines)

def view_quotes(atoms, max_sens='P'):
    quotes = [a for a in atoms if a['type'] == 'quote'
              and SENS_ORDER.get(a.get('sensitivity', 'N'), 0) <= SENS_ORDER[max_sens]]
    dropped = sum(1 for a in atoms if a['type'] == 'quote') - len(quotes)
    lines = [f'# 引语库 · 自动视图（脱敏≤{max_sens}）', '',
             f'> {len(quotes)} 条（已过滤敏感 {dropped} 条）', '']
    cur = None
    for a in sorted(quotes, key=lambda x: (x['session'], x['ts'])):
        if a['session'] != cur:
            lines.append(f'\n## {a["session"]}'); cur = a['session']
        lines.append(f"- [{a['ts']}] {a['speaker']}：{a['text']}")
    return '\n'.join(lines)

CSS = '''body{font-family:"PingFang SC",system-ui,sans-serif;max-width:860px;margin:40px auto;padding:0 20px;line-height:1.8;color:#1f2937;background:#fafaf8}
h1{font-size:26px;border-bottom:2px solid #4f46e5;padding-bottom:8px} h2{font-size:18px;color:#4f46e5;margin-top:28px}
.q{background:#fff;border:1px solid #e5e7eb;border-left:3px solid #4f46e5;border-radius:8px;padding:10px 14px;margin:8px 0}
.meta{color:#6b7280;font-size:12px} .tag{display:inline-block;font-size:11px;background:#eef2ff;color:#4f46e5;border-radius:99px;padding:1px 8px;margin-left:6px}
.badge{position:fixed;top:16px;right:16px;background:#f59e0b;color:#fff;border-radius:99px;padding:4px 12px;font-size:12px}'''

def view_share_html(atoms):
    quotes = [a for a in atoms if a['type'] == 'quote' and a.get('sensitivity') == 'N']
    methods = {}
    for a in [x for x in atoms if x['type'] == 'method']:
        key = next((k for k, kws in RULES if any(kw in a['title'] for kw in kws)), a['title'])
        methods.setdefault(key, set()).add(a['session'])
    top = sorted(methods.items(), key=lambda x: -len(x[1]))[:15]
    h = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>跨场知识精选 · 分享版</title>',
         f'<style>{CSS}</style></head><body><div class="badge">脱敏分享版</div>',
         '<h1>跨场知识精选（10 场对话沉淀）</h1>',
         f'<p class="meta">生成自原子库：引语 {len(quotes)} 条（已过滤价格/健康类）· 方法论 {len(methods)} 条</p>',
         '<h2>高频方法论 Top 15（按出现场次）</h2><ul>']
    for t, s in top:
        h.append(f'<li>{html.escape(t)} <span class="tag">{len(s)} 场</span></li>')
    h.append('</ul><h2>金句精选</h2>')
    cur = None
    for a in sorted(quotes, key=lambda x: (x['session'], x['ts'])):
        if a['session'] != cur:
            h.append(f'<h2>{a["session"]}</h2>'); cur = a['session']
        h.append(f'<div class="q"><span class="meta">[{a["ts"]}] {html.escape(a["speaker"])}</span><br>{html.escape(a["text"])}</div>')
    h.append('</body></html>')
    return '\n'.join(h)

atoms = load()
gdir = os.path.join(ROOT, '_全局资产')
os.makedirs(gdir, exist_ok=True)

if VIEW == 'methods':
    out = os.path.join(gdir, '方法论总库_视图.md')
    open(out, 'w').write(view_methods(atoms)); print(f'✓ {out}')
elif VIEW == 'quotes':
    out = os.path.join(gdir, f'引语库_视图_{MAX_SENS}.md')
    open(out, 'w').write(view_quotes(atoms, MAX_SENS)); print(f'✓ {out}')
elif VIEW == 'share':
    out = os.path.join(gdir, '分享版_跨场知识精选.html')
    open(out, 'w').write(view_share_html(atoms)); print(f'✓ {out}（可直接发给团队/客户）')
else:
    print('可用视图：methods / quotes [--max-sens N|P|H] / share'); sys.exit(1)
