#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_content.py <场次目录>

内容一致性审计（v3.3.3，检查项源自 2026-10-14 多维度代理评审沉淀——「评审→检查项」转化规则的首批产物）：
  A(err)  05 人物卡回合占比/绝对数 vs 01 正文实测（防旧口径虚高）
  B(warn) 01 正文的数字类事实行未被 06 收录（差异清单，人工过目后补录或豁免）
  C(warn) 01 死线/承诺关键词命中 vs 09 行动清单覆盖（时间词级对照，防死线漏收）
  D(warn) 00 待办表与 09 行动清单 Owner 冲突（同名行动不同 Owner=err 级标注）

退出码：err 级存在=1；仅 warn=0。
用法（pipeline_check.sh 已自动挂接，也可单跑）：
  python3 audit_content.py <场次目录>

Safety: Python stdlib only - no network, no subprocess, no dynamic execution.
"""
import re, sys, os, collections

QUOTE_RE = re.compile(r'\*\*【([^】]+)】\*\* \[(\d{1,2}:\d{2}(?::\d{2})?)\] (.+)')
# B：数值+货币/比例/规模单位紧邻（阿拉伯数字；中文数字不扫，噪声大由 C/D 兜）
NUM_UNIT_RE = re.compile(r'\d+(?:\.\d+)?\s*(?:万|亿|元|块钱|块|刀|美金|%|折|个月|人次|个人)')
# C：死线词（时间锚）与承诺词（行动锚）
DEADLINE_WORDS = ['明天', '后天', '大后天', '周五', '周四', '下周', '这周', '本周',
                  '月底', '年底', '年前', '死线', '之前要', '之前给', '之前把', '到期']
PROMISE_WORDS = ['回头我', '到时候我', '我给你做', '我帮你', '我帮你做', '我发你',
                 '我来弄', '我来做', '我给你', '我去弄']


def load_body(d):
    p = os.path.join(d, '01_清洗稿.md')
    if not os.path.exists(p):
        return ''
    s = open(p, encoding='utf-8').read()
    return s.split('# 全场清洗逐字稿', 1)[-1].split('## 附录 A', 1)[0]


def rd(d, name):
    p = os.path.join(d, name)
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ''


def audit_a(d, body, errs):
    """05 占比/绝对数 vs 01 实测"""
    p5 = rd(d, '05_人物角色卡.md')
    if not (p5 and body):
        return
    # v3.3.5：绝对回合数为可选口径（05 契约样例只写「约 X%」），占比为必校验项
    actual = collections.Counter(w for w, _, _ in QUOTE_RE.findall(body))
    total = sum(actual.values())
    if not total:
        return
    for blk in re.split(r'\n## ', p5)[1:]:
        name = re.split(r'[（(]', blk.split('\n', 1)[0].strip())[0].strip()
        m = re.search(r'\*\*发言量占比\*\*：约 (\d+)%（?(?:(\d+)(?:/(\d+))? 回合）?)?', blk)
        if not m or name not in actual:
            continue
        pct_claim, n_claim = int(m.group(1)), int(m.group(2))
        pct_real = round(actual[name] / total * 100)
        if abs(pct_claim - pct_real) > 2:
            errs.append(f'A|05人物卡[{name}] 占比声明 {pct_claim}% vs 实测 {pct_real}%'
                        f'（{actual[name]}/{total}）——用清洗后口径重算')
        if m.group(2) and int(m.group(2)) != actual[name]:
            errs.append(f'A|05人物卡[{name}] 回合数声明 {m.group(2)} vs 实测 {actual[name]}——旧口径未更新')


def audit_b(d, body, warns):
    """01 数字行 vs 06 收录差异"""
    p6 = rd(d, '06_关键数据速查.md')
    if not (body and p6):
        return
    got = set(re.findall(r'\d+(?:\.\d+)?\s*(?:万|亿|元|块|刀|美金|%|折|个月|人|个|台)', p6))
    seen, missing = set(), []
    for w, ts, txt in QUOTE_RE.findall(body):
        for num in NUM_UNIT_RE.findall(txt):
            if num in got or num in seen or len(num) <= 1:
                continue
            seen.add(num)
            missing.append(f'  · {num}｜{w}·[{ts}]｜{txt[:44]}')
    if missing:
        warns.append(f'B|06 数据覆盖：01 有 {len(missing)} 个数值串未见 06 收录'
                     '（人工过目：该补的补录，闲聊数字可忽略）')
        warns.extend(missing[:30])
        if len(missing) > 30:
            warns.append(f'  · …另有 {len(missing) - 30} 个未列出')


def audit_c(d, body, warns):
    """死线/承诺词 vs 09 覆盖"""
    p9 = rd(d, '09_战略诊断与行动清单.md')
    if not body:
        return
    hits = collections.Counter()
    examples = collections.defaultdict(list)
    for w, ts, txt in QUOTE_RE.findall(body):
        for kw in DEADLINE_WORDS + PROMISE_WORDS:
            if kw in txt:
                hits[kw] += 1
                if len(examples[kw]) < 2:
                    examples[kw].append(f'{w}·[{ts}] {txt[:40]}')
    if not hits:
        return
    uncovered = []
    for kw, n in hits.most_common():
        in9 = p9.count(kw) if p9 else 0
        if in9 == 0:
            uncovered.append(f'  · 「{kw}」01 命中 {n} 次 / 09 出现 0 次｜如：' +
                             '；'.join(examples[kw][:1]))
    if uncovered:
        warns.append(f'C|09 死线/承诺覆盖：{len(uncovered)} 个时间/承诺词在 01 有命中但 09 全无对应'
                     '（逐条核对：真待办补入，闲聊提及可豁免）')
        warns.extend(uncovered[:12])


def audit_d(d, errs, warns):
    """00 待办表 vs 09 行动清单"""
    p0, p9 = rd(d, '00_执行摘要.md'), rd(d, '09_战略诊断与行动清单.md')
    if not (p0 and p9):
        return

    def rows(md, n_cols):
        out = []
        for ln in md.splitlines():
            if ln.startswith('|') and '---' not in ln:
                cells = [c.strip() for c in ln.strip('|').split('|')]
                if len(cells) >= n_cols and not set(cells[0]) <= set('- '):
                    out.append(cells)
        return out

    def owners(s):
        s = re.sub(r'（[^）]*）|\([^)]*\)', '', s)  # 剥括注（「（B 帮整）」是补充说明不是第二 Owner）
        return {x for x in re.split(r'[×,/，、\s]+', s) if x and x != '待定'}

    def grams(s):
        s = re.sub(r'（[^）]*）|\([^)]*\)', '', s)  # 剥括注（「（B 帮整）」类补充说明干扰相似度）
        s = re.sub(r'[^\w一-鿿]', '', s)
        return {s[i:i + 2] for i in range(len(s) - 1)} or {s}

    t0 = [r for r in rows(p0, 3) if r[0] not in ('行动',)]
    t9 = [r for r in rows(p9, 5) if not re.match(r'^P?\d*$', r[0]) or r[0].startswith('P')]
    t9 = [r for r in t9 if len(r) >= 5 and r[0].startswith('P')]
    for r0 in t0:
        act, own0 = r0[0], owners(r0[1] if len(r0) > 1 else '')
        best, best_j = None, 0.0
        for r9 in t9:
            j = len(grams(act) & grams(r9[1])) / max(1, len(grams(act) | grams(r9[1])))
            if j > best_j:
                best, best_j = r9, j
        if best and best_j >= 0.3:
            own9 = owners(best[2])
            if own0 and own9 and not (own0 & own9):
                errs.append(f'D|Owner 冲突：00「{act[:20]}」={r0[1]} vs 09「{best[1][:20]}」={best[2]}'
                            '——回原文核对说话人')
        elif best_j < 0.3:
            warns.append(f'D|00 待办「{act[:26]}」在 09 无相近行动（核对是否漏入）')


def main():
    if len(sys.argv) < 2:
        print('用法: audit_content.py <场次目录>'); return 2
    d = sys.argv[1]
    if not os.path.isdir(d):
        print(f'✗ 目录不存在: {d}'); return 1
    body = load_body(d)
    errs, warns = [], []
    audit_a(d, body, errs)
    audit_b(d, body, warns)
    audit_c(d, body, warns)
    audit_d(d, errs, warns)
    for w in warns:
        print(f'  ⚠ {w}')
    for e in errs:
        print(f'  ✗ {e}')
    print(f'audit_content: err {len(errs)}，warn {len(warns)}'
          + ('（err 需修复后重跑）' if errs else ''))
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
