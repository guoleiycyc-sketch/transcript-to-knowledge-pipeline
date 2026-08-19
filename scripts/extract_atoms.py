#!/usr/bin/env python3
"""extract_atoms.py — 从各场次知识包抽取原子到 atoms.jsonl（第三批：单库多视图的数据层）

用法：
  python3 extract_atoms.py <录音项目根> [场次目录...]

- 不传场次目录时自动扫描 <根>/AI企业应用战略_2026-08/*_2026-08-*/ 与 <根>/*_2026-08-*/（含 03_方法论清单.md 的目录）
- 原子类型：quote / method / insight / person / decision
- 重复执行安全：按 id 去重，重跑只增量
"""
import json, os, re, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
EXTRA = sys.argv[2:]

SENS_PAT = re.compile(r'\d+\s*万|\d+\s*块钱|报价|一年是|元/|净收|利润|分红|底薪|结算|可以做决定')
HEALTH_PAT = re.compile(r'视网膜|病|手术|住院|身体')

def sens_level(text):
    if HEALTH_PAT.search(text): return 'H'
    if SENS_PAT.search(text): return 'P'
    return 'N'

def sessions():
    out = []
    d = os.path.join(ROOT, 'AI企业应用战略_2026-08')
    if os.path.isdir(d):
        for x in sorted(os.listdir(d)):
            p = os.path.join(d, x)
            if os.path.isdir(p) and re.search(r'_2026-\d{2}-\d{2}$', x) and os.path.exists(os.path.join(p, '03_方法论清单.md')):
                out.append(p)
    for x in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, x)
        if os.path.isdir(p) and re.search(r'_2026-\d{2}-\d{2}$', x) and os.path.exists(os.path.join(p, '03_方法论清单.md')):
            out.append(p)
    out += EXTRA
    return sorted(set(out))

def sid_of(path):
    m = re.search(r'(2026-\d{2}-\d{2})', path)
    return m.group(1).replace('2026-', '') if m else os.path.basename(path)[:12]

def extract():
    atoms = []
    for p in sessions():
        sid = sid_of(p)
        # quotes（README 金句速查，回退 01 附录 B）
        src = ''
        rp = os.path.join(p, 'README.md')
        if os.path.exists(rp): src = open(rp).read()
        gs = re.findall(r'^\d+\. \*\*【([^】]+)】\*\* \[([^\]]+)\] (.+)$', src, re.M)
        if not gs:
            op = os.path.join(p, '01_清洗稿.md')
            if os.path.exists(op):
                gs = re.findall(r'^\d+\. \*\*【([^】]+)】\*\* \[([^\]]+)\] (.+)$', open(op).read(), re.M)
        for i, (spk, ts, text) in enumerate(gs, 1):
            atoms.append(dict(id=f'q-{sid}-{i:02d}', type='quote', session=sid,
                              ts=ts, speaker=spk, text=text.strip(),
                              sensitivity=sens_level(text)))
        # methods
        mp = os.path.join(p, '03_方法论清单.md')
        if os.path.exists(mp):
            for i, t in enumerate(re.findall(r'^## \d+\. (.+)$', open(mp).read(), re.M), 1):
                atoms.append(dict(id=f'm-{sid}-{i:02d}', type='method', session=sid, title=t.strip()))
        # insights
        ip = os.path.join(p, '08_洞察卡片.md')
        if os.path.exists(ip):
            for i, t in enumerate(re.findall(r'^## 卡 \d+ · (.+)$', open(ip).read(), re.M), 1):
                atoms.append(dict(id=f'i-{sid}-{i:02d}', type='insight', session=sid, title=t.strip()))
        # persons（05 人物卡标题）
        pp = os.path.join(p, '05_人物角色卡.md')
        if os.path.exists(pp):
            for t in re.findall(r'^## ([^#\n]+)$', open(pp).read(), re.M):
                t = t.strip()
                if t and '（被提及' not in t and not t.startswith('占比'):
                    atoms.append(dict(id=f'p-{sid}-{t[:6]}', type='person', session=sid, name=t))
    return atoms

def main():
    out_path = os.path.join(ROOT, '_全局资产', 'atoms.jsonl')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    existing = {}
    if os.path.exists(out_path):
        for line in open(out_path):
            try: a = json.loads(line); existing[a['id']] = a
            except json.JSONDecodeError: pass
    atoms = extract()
    n_new = 0
    for a in atoms:
        if a['id'] not in existing:
            existing[a['id']] = a; n_new += 1
    with open(out_path, 'w') as f:
        for a in existing.values():
            f.write(json.dumps(a, ensure_ascii=False) + '\n')
    from collections import Counter
    c = Counter(a['type'] for a in existing.values())
    print(f"atoms.jsonl 共 {len(existing)} 原子：{dict(c)}；本次新增 {n_new}")
    print(f"位置：{out_path}")

if __name__ == '__main__':
    main()
