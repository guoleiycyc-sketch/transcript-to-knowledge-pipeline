#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_report.py — 清洗忠实度审计：原稿 vs 清洗稿的机械对比报告

为什么存在：清洗稿的忠实度目前靠「人写的忠实性说明」。客户最在意「AI 改没改我的
原话」——本脚本把可机械计算的部分算出来，作为交付时的信任凭证
（「诚实标注 > 完美无瑕」的代码化）。

输出指标：
  原稿回合数/字符数 vs 清洗回合数/字符数（合并比、字符比）
  ASR 订正条数（01 头部对照表）、[ASR/存疑] 条数
  结构自检：附录 A-D 在位、锚点残留=0、正文无加粗、无无时间戳续段

诚实边界（报告会打印）：字符差异 = 口水删除 + 回合合并去重 + 标点补齐的总和，
不是净删除量；本报告不做逐句语义比对（那是 verify_quotes 对引文的职责）。

支持的原稿格式（自动探测，探测不到 exit 2）：
  **【人】** [ts] 内容      管线格式
  人 [ts] 内容              妙记类（行首可有 emoji 前缀）
  人(HH:MM:SS): 内容        会议平台导出类

用法：python3 scripts/diff_report.py <原始转写.md> <场次目录>
安全声明：stdlib-only / 无网络 / 无子进程 / 只读。
"""
import re
import sys
from pathlib import Path

PAT_CLEAN = re.compile(r'^\*\*【([^】]+)】\*\* \[(\d{2,3}:\d{2}(?::\d{2})?)\] (.*)$')
PAT_MIAOJI = re.compile(r'^.{0,24}?\[(\d{2,3}:\d{2}(?::\d{2})?)\]\s*(.*)$')
PAT_MEETING = re.compile(r'^([^(（]{1,20})[（(](\d{2,3}:\d{2}(?::\d{2})?)[）)]:\s*(.*)$')
TS_INLINE = re.compile(r'\[(\d{2,3}:\d{2}(?::\d{2})?)\]')


def parse_raw(path: Path):
    """原稿 → [(说话人?, 时间戳?, 正文), ...]；按格式自动探测。"""
    turns, fmt = [], None
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = PAT_CLEAN.match(ln)
        if m:
            fmt = fmt or "管线格式"
            turns.append((m.group(1), m.group(2), m.group(3)))
            continue
        m = PAT_MEETING.match(ln)
        if m:
            fmt = fmt or "会议导出格式"
            turns.append((m.group(1).strip(), m.group(2), m.group(3)))
            continue
        m = PAT_MIAOJI.match(ln)
        if m:
            fmt = fmt or "妙记格式"
            turns.append(("", m.group(1), m.group(2)))
            continue
        if turns:  # 换行续行并入上一块
            sp, ts, txt = turns[-1]
            turns[-1] = (sp, ts, txt + ln)
    return turns, fmt or ""


def parse_clean(pack: Path):
    """01 清洗稿 → 正文回合 [(人, ts, 正文), ...]（跳过头部引用块与附录）。"""
    body = (pack / "01_清洗稿.md").read_text(encoding="utf-8")
    body = body.split("# 全场清洗逐字稿", 1)[-1]
    body = re.split(r"^## 附录 [A-D]", body, flags=re.M)[0]
    turns = []
    for ln in body.splitlines():
        m = PAT_CLEAN.match(ln.strip())
        if m:
            turns.append((m.group(1), m.group(2), m.group(3)))
    return body, turns


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    raw_path, pack = Path(sys.argv[1]), Path(sys.argv[2])
    if not raw_path.exists() or not (pack / "01_清洗稿.md").exists():
        print("✗ 原稿或清洗稿不存在"); return 2

    raw_turns, fmt = parse_raw(raw_path)
    if not raw_turns:
        print("✗ 原稿格式未识别（支持：管线 / 妙记 / 会议导出）"); return 2
    body, clean_turns = parse_clean(pack)

    raw_chars = sum(len(t[2]) for t in raw_turns)
    clean_chars = sum(len(t[2]) for t in clean_turns)
    full_01 = (pack / "01_清洗稿.md").read_text(encoding="utf-8")
    header_01 = full_01.split("# 全场清洗逐字稿", 1)[0]
    fixes = max(0, len(re.findall(r"^\| [^|]+ \| [^|]+ \|", header_01, flags=re.M)) - 1)  # -1 表头
    unsure = body.count("[ASR/存疑]")
    has_appendix = {k: (f"## 附录 {k}" in full_01) for k in "ABCD"}
    anchors = full_01.count("APPEND_MARKER")
    bold_in_body = len([ln for ln in body.splitlines() if ln.strip().startswith("**【") and ln.strip().endswith("**") and not PAT_CLEAN.match(ln.strip())])
    cont_lines = len([ln for ln in body.splitlines()
                      if ln.strip() and not ln.lstrip().startswith(("**【", "#", "|", ">", "-"))])

    print(f"清洗忠实度报告：{pack.name}")
    print(f"  原稿（{fmt}）：{len(raw_turns)} 块 / {raw_chars} 字")
    print(f"  清洗稿      ：{len(clean_turns)} 回合 / {clean_chars} 字")
    print(f"  回合合并比  ：{len(raw_turns) and round(len(clean_turns) / len(raw_turns), 2) or '—'}"
          f"（清洗/原稿；<1 = 同人碎片被合并）")
    print(f"  字符比      ：{raw_chars and round(clean_chars / raw_chars, 2) or '—'}"
          f"（含口水删除+合并去重+标点补齐，非净删除量）")
    print(f"  ASR 订正    ：{fixes} 条（对照表行数，含表头请自行 -1）")
    print(f"  存疑标注    ：{unsure} 处 [ASR/存疑]")
    print(f"  附录在位    ：{' '.join(k + ('✓' if v else '✗') for k, v in has_appendix.items())}")
    print(f"  结构自检    ：锚点残留={anchors}（应0） 疑似续行={cont_lines}（应0，>0 疑无时间戳续段）")
    print("  诚实边界：字符比不区分删除口水与删减内容；逐句核证走 verify_quotes（引文层）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
