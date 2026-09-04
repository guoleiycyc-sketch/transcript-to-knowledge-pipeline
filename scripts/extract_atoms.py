#!/usr/bin/env python3
"""extract_atoms.py — 从各场次知识包抽取原子到 atoms.jsonl（第三批：单库多视图的数据层）

用法：
  python3 extract_atoms.py <录音项目根> [场次目录...]

- 不传场次目录时**递归扫描**整个项目树（跳过 .git/_知识库/录音来源 等），
  凡「目录名以 _YYYY-MM-DD 结尾 且 含 03_方法论清单.md」即视为场次。
  旧版只扫固定两层，嵌套场次（E合作/02_沟通与会议/、_成果目录/ 等）
  曾两次漏抽（2026-08-25 某场次、2026-09-03 某场次），勿回退
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

# 递归扫描时跳过的目录：镜像仓会重复抽取、来源层只有原始转写
SKIP_DIRS = {'.git', '_知识库', '录音来源', '_工具与个人', '__pycache__', 'node_modules'}

def sessions():
    out = find_session_dirs(ROOT)
    out += EXTRA
    return sorted(set(out))

def find_session_dirs(root):
    """递归发现场次目录（含 03_方法论清单.md 且目录名 _YYYY-MM-DD 结尾）。
    命中后不再向场次目录内部下钻。"""
    out = []
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return out
    for x in entries:
        p = os.path.join(root, x)
        if not os.path.isdir(p) or x in SKIP_DIRS:
            continue
        # `_YYYY-MM-DD` 结尾，或三场连读的双日期形态 `_YYYY-MM-DD_MM-DD`（如启动期报价_2026-08-31_09-02）
        if re.search(r'_\d{4}-\d{2}-\d{2}(_\d{2}-\d{2})?$', x) and os.path.exists(os.path.join(p, '03_方法论清单.md')):
            out.append(p)
            continue
        out += find_session_dirs(p)
    return out

def sid_of(path):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', path)
    return m.group(1)[5:] if m else os.path.basename(path)[:12]

def date_suffix_map(dirs):
    """同日多场按目录名排序：第一场无后缀（兼容存量 atoms 的 q-09-03-xx 格式），
    第二场起加 b/c/d…（2026-09-04 实战 bug：同日两场 sid 撞号，后入库场的
    7 条 method 被先入库场按 id 去重吞并）。"""
    from collections import defaultdict
    by_date = defaultdict(list)
    for d in dirs:
        by_date[sid_of(d)].append(d)
    mapping = {}
    for date, lst in by_date.items():
        lst.sort()
        for i, d in enumerate(lst):
            mapping[os.path.abspath(d)] = date + ('' if i == 0 else chr(ord('a') + i))
    return mapping

def extract():
    atoms = []
    sess = sessions()
    uid_map = date_suffix_map(sess)
    for p in sess:
        sid = uid_map.get(os.path.abspath(p), sid_of(p))
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
