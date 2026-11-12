#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_module_contract.py —— 模块契约核对器（P60 防再发工具化，v1）

背景（坑库 P60，2026-11-12，175-178 批）：机器门禁（结构存在/引文逐字）全绿，
但 02 段文件被压成 3 行、00a 自创结构、03 丢「怎么用」、08 漏洞察地图——
契约是人工自检清单，被「机器绿=过关」心态跳过。本脚本把 references/03 尾部
「退出本阶段的自检清单」的硬项变成机器可查，堵住这个盲区。

用法: python3 check_module_contract.py <场次目录>
退出码: 0=通过(允许 WARN)；1=存在 FAIL；2=参数/目录错误
原则: 只查「存在即须守契约」的模块（专项档天然豁免未产出的模块）；
      分档嫌疑给 WARN 不给 FAIL（00a 缺席但 02-09 齐全=可疑降档）。
"""
import os, re, sys, glob

def rd(p):
    try:
        return open(p, encoding='utf-8').read()
    except OSError:
        return ''

def main():
    if len(sys.argv) != 2:
        print('用法: python3 check_module_contract.py <场次目录>'); sys.exit(2)
    d = sys.argv[1]
    if not os.path.isdir(d):
        print(f'✗ 目录不存在: {d}'); sys.exit(2)

    fails, warns, passes = [], [], []
    def ok(msg): passes.append(msg)
    def warn(msg): warns.append(msg)
    def fail(msg): fails.append(msg)

    has = lambda name: os.path.exists(os.path.join(d, name))
    has00a, has00, has01 = has('00a_一分钟简报.md'), has('00_执行摘要.md'), has('01_清洗稿.md')

    if not has01:
        fail('缺 01_清洗稿.md（本检查器面向已产出知识包的场次）')

    # ── 00a 五段契约 ──────────────────────────────
    if has00a:
        a = rd(os.path.join(d, '00a_一分钟简报.md'))
        for sec in ['## 一句话结论', '## 三条核心', '## 决定与待办', '## 一个提醒', '## 值得深读']:
            (ok if sec in a else fail)(f'00a 五段契约: {sec}' + ('' if sec in a else ' 缺失'))
        m = re.search(r'^## 三条核心\s*$(.*?)^## ', a, re.M | re.S)
        if m:
            items = [x for x in m.group(1).strip().split('\n') if re.match(r'^\d+\. ', x)]
            short = [x for x in items if len(x) < 25]
            if items and short:
                fail(f'00a 三条核心存在空电报头（<{25}字 {len(short)} 条，应写成完整叙事句）')
            elif items:
                ok('00a 三条核心为叙事句')
    else:
        mods = [n for n in ['03_方法论清单.md','04_术语表.md','05_人物角色卡.md','08_洞察卡片.md','09_战略诊断与行动清单.md'] if has(n)]
        if mods:
            warn(f'00a 缺失但存在 {len(mods)} 个提炼模块——分档嫌疑（轻加强及以上应有 00a），请复核产前分档')

    # ── 02 段文件契约 ──────────────────────────────
    segdir = os.path.join(d, '02_主题整理')
    if os.path.isdir(segdir):
        segs = sorted(glob.glob(os.path.join(segdir, '第*.md')))
        if not segs and not has('02_主题整理.md'):
            warn('02_主题整理/ 目录为空')
        nums = []
        for f in segs:
            b = os.path.basename(f)
            m = re.match(r'第(\d+)段_', b)
            if not m:
                fail(f'02 段文件名不合契约: {b}（应为 第N段_主题.md）'); continue
            nums.append(int(m.group(1)))
            s = rd(f)
            if not re.match(r'# 第\d+段 · ', s):
                fail(f'02 {b} 标题行不合契约（应为 `# 第N段 · 标题`）')
            for sec in ['## 摘要', '## 段结论']:
                if sec not in s:
                    fail(f'02 {b} 缺 {sec}')
            body_lines = len([l for l in s.split('\n') if l.strip()])
            has_quote = ('## 金句' in s) or ('## 原文节选' in s)
            if body_lines < 8 or not has_quote:
                fail(f'02 {b} 疑似降规格（{body_lines} 行/金句或原文节选{"有" if has_quote else "无"}；先例=31 行完整结构：摘要+详细分析+段结论+金句+原文节选）')
        if nums and sorted(nums) != list(range(1, len(nums) + 1)):
            fail(f'02 段号不连续: {nums}')
        elif segs:
            ok(f'02 段文件 {len(segs)} 个，编号连续')

    # ── 03 卡片式契约 ──────────────────────────────
    if has('03_方法论清单.md'):
        t = rd(os.path.join(d, '03_方法论清单.md'))
        n_card = len(re.findall(r'^## \d+\. ', t, re.M))
        if n_card == 0:
            fail('03 非卡片式（应 `## N. 名称` 卡片，先例格式）')
        else:
            if '怎么用' not in t:
                fail('03 卡片缺「怎么用」字段')
            else:
                ok(f'03 卡片式 {n_card} 条含怎么用')

    # ── 05 人物卡契约 ──────────────────────────────
    if has('05_人物角色卡.md'):
        s = rd(os.path.join(d, '05_人物角色卡.md'))
        n_checked = 0
        for m in re.finditer(r'^## ([^\n#(]+)', s, re.M):
            name = m.group(1).strip()
            if not name: continue
            head = s[m.start():m.start() + 250]
            if '简记' in head:  # 未出场聚合段豁免
                continue
            n_checked += 1
            seg = s[m.start():]
            nxt = re.search(r'^## ', seg[3:], re.M)
            blk = seg[:nxt.start() + 3] if nxt else seg
            if '**背景与立场**' not in blk:
                fail(f'05 出场卡「{name}」缺 **背景与立场** 字段头')
            elif not re.search(r'约 ?\d+%', blk):
                fail(f'05 出场卡「{name}」缺「约 XX%」发言量')
        if n_checked:
            ok(f'05 出场卡 {n_checked} 张字段齐')

    # ── 06 口径标注 ────────────────────────────────
    if has('06_关键数据速查.md'):
        s = rd(os.path.join(d, '06_关键数据速查.md'))
        if re.search(r'【约】|【存疑】|【口径】|照录|未核实', s):
            ok('06 有口径标注说明')
        else:
            fail('06 缺口径标注说明（【约】/【存疑】/【口径】或「照录未核实」）')

    # ── 07 母题与图 ────────────────────────────────
    if has('07_议题关联地图.md'):
        s = rd(os.path.join(d, '07_议题关联地图.md'))
        if '**母题**' not in s: fail('07 缺 **母题**： 行')
        if '```' not in s: fail('07 缺 ASCII 图代码块')
        if '**母题**' in s and '```' in s: ok('07 母题+图齐')

    # ── 08 洞察卡契约 ──────────────────────────────
    if has('08_洞察卡片.md'):
        s = rd(os.path.join(d, '08_洞察卡片.md'))
        cards = re.split(r'\n## 卡 ', s)[1:]
        if not cards: fail('08 无卡片（应 `## 卡 N · 标题`）')
        for c in cards:
            cid = c.split('·')[0].strip()[:12]
            for fld in ['**核心**', '**证据**', '**启示**', '**反方**']:
                if fld not in c:
                    fail(f'08 卡{cid} 缺 {fld}')
        if '## 洞察地图' not in s: fail('08 缺 ## 洞察地图')
        if cards and '## 洞察地图' in s: ok(f'08 卡 {len(cards)} 张四字段+反方+地图齐')

    # ── 09 上期回顾 ────────────────────────────────
    if has('09_战略诊断与行动清单.md'):
        s = rd(os.path.join(d, '09_战略诊断与行动清单.md'))
        (ok if '上期' in s else fail)('09 上期行动回顾' + ('' if '上期' in s else ' 缺失'))

    # ── README ────────────────────────────────────
    r = rd(os.path.join(d, 'README.md'))
    if not r:
        fail('缺 README.md')
    else:
        if '.html' not in r: fail('README 缺 HTML 链接')
        if '跨场' not in r: warn('README 缺跨场呼应段')
        if '.html' in r: ok('README 含 HTML 链接')

    # ── 汇总 ──────────────────────────────────────
    print(f'[模块契约] PASS {len(passes)} ｜ WARN {len(warns)} ｜ FAIL {len(fails)}')
    for w in warns: print(f'  ⚠ {w}')
    for f in fails: print(f'  ✗ {f}')
    if fails:
        print('存在契约违例（P60 类降规格风险）——修复后再发布'); sys.exit(1)
    print('模块契约全部通过')
    sys.exit(0)

if __name__ == '__main__':
    main()
