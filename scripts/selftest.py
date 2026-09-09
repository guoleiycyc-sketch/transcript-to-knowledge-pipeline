#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest.py — 端到端冒烟自检（渲染 + 引文核证全链）

把 example/ 示例场复制到临时目录 → 删掉成品 HTML 从 md 全新生成 → verify_quotes
引文核证 → 断言关键契约（金句卡/锚点/人物/内容在位）。

何时跑：改渲染器（build_html/render_pack）、校验器（verify_quotes）、或
references/03 模板契约后必跑——与 regression_check 互补：那边断言渲染细节，
这边断言「md 契约 → 渲染 → 校验」全链。安全声明：stdlib-only / 无网络 / 无子进程
执行以外的新副作用（子进程仅调用本目录脚本，临时目录即用即弃）。

用法：python3 scripts/selftest.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLE = SCRIPT_DIR.parent / "example" / "示例场_SaaS定价讨论_2026-01-15"


def main() -> int:
    if not EXAMPLE.exists():
        print(f"✗ 示例场缺失：{EXAMPLE}")
        return 1
    fails = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / EXAMPLE.name
        shutil.copytree(EXAMPLE, d)
        for f in d.glob("*.html"):
            f.unlink()  # 从 md 全新生成，不吃存量成品

        # 1. 渲染全链
        r = subprocess.run([sys.executable, str(SCRIPT_DIR / "render_pack.py"), str(d)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fails.append(f"render_pack 退出码 {r.returncode}: {(r.stderr or r.stdout)[-300:]}")
        html = d / f"{d.name}.html"
        if not html.exists():
            fails.append("HTML 未生成")
        else:
            t = html.read_text(encoding="utf-8")
            for needle, name in [('class="quote', "金句卡"),
                                 ('id="insight-1"', "洞察卡锚点"),
                                 ('id="people"', "人物区锚点"),
                                 ("陈岸", "人物内容"),
                                 ("看不懂账单", "金句内容"),
                                 ("母题", "总览母题")]:
                if needle not in t:
                    fails.append(f"HTML 缺 {name}（未命中 {needle!r}）")
            if "死锚点" in r.stdout:
                fails.append(f"渲染自检报死锚点: {r.stdout[:200]}")

        # 2. 引文核证（02/05/08 引文逐字 + 时间戳命中 01）
        v = subprocess.run([sys.executable, str(SCRIPT_DIR / "verify_quotes.py"), str(d)],
                           capture_output=True, text=True)
        if v.returncode != 0 or "硬伤 0" not in (v.stdout + v.stderr):
            fails.append(f"verify_quotes 未过: {(v.stdout + v.stderr)[-300:]}")

    if fails:
        print("✗ selftest 失败：")
        for f in fails:
            print("  -", f)
        return 1
    print("✓ selftest 通过（md 契约 → 渲染 → 引文核证 全链绿灯）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
