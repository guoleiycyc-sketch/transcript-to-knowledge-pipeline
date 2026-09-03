#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_quotes.py <场次目录>

洞察卡/主题段引文的忠实性校验（v2 2026-08-22 新增，源自 08-21 场全量审校）：
  1. 时间戳存在性：02/05/08/README 中长格式引文 **【人】** [ts] 的 (人,ts)
     必须命中 01 正文的某个回合首（合并段须引用段首时间戳）。
  2. 引文逐字：引文按省略号/破折号切段后，归一化（去标点/引号/ASR 标注）
     必须是 01 对应回合的子串。金句原则：一字不改。
  3. 反方质量：08 的 **反方**： 字段做启发式——过短或匹配敷衍模式 → 警告。

退出码：硬伤（时间戳错位/不逐字）=1；仅警告 =0。

用法（pipeline_check.sh 已自动挂接，也可单跑）：
  python3 verify_quotes.py <场次目录>
"""
import re, sys, glob, os

HOLLOW_PATTERNS = [
    r'也可能不成立', r'要看具体情况', r'因人而异', r'凡事都有两面',
    r'存在不确定性', r'需要进一步(验证|观察)', r'不能一概而论', r'仅供参考',
    r'未必(总是)?适用', r'有一定(局限|风险)$',
]
QUOTE_RE = re.compile(r'\*\*【([^】]+)】\*\* \[(\d{1,2}:\d{2}(?::\d{2})?)\] (.+)')

def norm(s: str) -> str:
    # 先剥离圆括号内容（写作括注/清洗括注两侧对称豁免：引文主干仍须逐字），
    # 再去空白+中英标点+引号+ASR标注记号（引号种类与省略号处理曾致 08-21 审校误报，勿删）
    s = re.sub(r'（[^）]*）', '', s)
    return re.sub(r'[\s，。、！？：；（）“”‘’「」『』——…·\[\]`／/""\'\'?？,;:!\-\*]', '', s)

def load_turns(dirpath: str):
    """01 正文回合：跳过头部（对照表登记源时间戳合法）与附录（说明性引用）。"""
    p = os.path.join(dirpath, '01_清洗稿.md')
    if not os.path.exists(p):
        return {}
    s = open(p, encoding='utf-8').read()
    body = s.split('# 全场清洗逐字稿', 1)[-1]
    body = body.split('## 附录 A', 1)[0]
    return {(w, t): txt for w, t, txt in QUOTE_RE.findall(body)}

def main():
    if len(sys.argv) < 2:
        print('用法: verify_quotes.py <场次目录>'); return 2
    d = sys.argv[1]
    turn_map = load_turns(d)
    if not turn_map:
        print('（无 01 清洗稿或无正文回合，跳过）'); return 0

    targets = ['05_人物角色卡.md', '08_洞察卡片.md', 'README.md'] + \
              sorted(glob.glob(os.path.join(d, '02_主题整理', '*.md')))
    fails, warns = [], []
    for f in targets:
        fp = f if os.path.isabs(f) else os.path.join(d, f)
        if not os.path.exists(fp):
            continue
        rel = os.path.basename(fp)
        txt = open(fp, encoding='utf-8').read()
        for who, ts, quote in QUOTE_RE.findall(txt):
            base = turn_map.get((who, ts))
            if base is None:
                fails.append(f'{rel}: [{ts}]{who} 时间戳不在 01 正文（疑指向被合并段，应改段首）')
                continue
            for seg_raw in re.split(r'…+|\.\.\.+|——', quote):
                seg = norm(seg_raw)
                if len(seg) > 10 and seg not in norm(base):
                    fails.append(f'{rel}: [{ts}]{who} 引文不逐字:「{seg_raw[:36]}」')
        # 孤立时间戳（软警告：场景描述/头部说明合法）
        for ts in set(re.findall(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]', txt)):
            if not any(t == ts for _, t in turn_map):
                warns.append(f'{rel}: 孤立时间戳 [{ts}]（场景描述则可，引用则改指向）')

    # 反方质量启发式（只警告，不阻断——防误杀真实反方）
    p8 = os.path.join(d, '08_洞察卡片.md')
    if os.path.exists(p8):
        s8 = open(p8, encoding='utf-8').read()
        cur_card = '?'
        for line in s8.splitlines():
            m = re.match(r'^## 卡 (\d+)', line)
            if m:
                cur_card = m.group(1); continue
            m = re.match(r'^\*\*反方\*\*[:：]\s*(.+)$', line.strip())
            if m:
                content = m.group(1)
                if len(norm(content)) < 12:
                    warns.append(f'08 卡{cur_card}: 反方过短（<12 字），疑空洞')
                for pat in HOLLOW_PATTERNS:
                    if re.search(pat, content):
                        warns.append(f'08 卡{cur_card}: 反方疑似敷衍模式「{pat}」——须落到场内对立引文/明确边界条件')
                        break

    for w in warns:
        print(f'  ⚠ {w}')
    for f_ in fails:
        print(f'  ✗ {f_}')
    print(f'verify_quotes: 硬伤 {len(fails)}，警告 {len(warns)}')
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main())
