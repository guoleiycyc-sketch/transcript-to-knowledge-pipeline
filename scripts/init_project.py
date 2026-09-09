#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_project.py — 初始化多场次知识库项目骨架（幂等：已存在一律跳过不覆盖）

生成三件套：
  pipeline.config.json   管线配置（--delegation 时启用单场委派模式，见 references/08）
  _词表.md               ASR 订正累积词表（清洗先查、新订正回填，见 references/02）
  录音来源/_索引.md       转写来源索引（防重复清洗，见 references/07）

用法：python3 scripts/init_project.py <项目根> [--delegation]
安全声明：stdlib-only / 无网络 / 无子进程 / 只在目标目录创建三个新文件。
"""
import json
import sys
from pathlib import Path

LEXICON = """# ASR 订正词表（累积）

> 清洗前先查本表（本场命中直接还原进正文）；本场新订正回填到此。
> 只收跨场可复用的确定订正；单场特例留在该场 01 头部对照表，不进本表。

| 原词（ASR） | 还原 | 说明 |
|---|---|---|
| （示例）私总会 | 私董会 | 行业术语误听，按需替换 |
"""

INDEX = """# 转写来源索引

> 新转写落盘后登记一行；清洗完成后状态列改「已清洗→场次目录」。

| 文件名 | 日期 | 状态 | 场次目录 |
|---|---|---|---|
"""


def write_if_absent(path: Path, content: str, label: str) -> bool:
    if path.exists():
        print(f"  跳过 {label}（已存在）: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {label}: {path}")
    return True


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).resolve()
    delegation = "--delegation" in sys.argv
    root.mkdir(parents=True, exist_ok=True)

    config = {"delegation": {"enabled": delegation}}
    print(f"初始化知识库项目骨架 → {root}" + ("（委派模式开）" if delegation else ""))
    write_if_absent(root / "pipeline.config.json",
                    json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                    "管线配置")
    write_if_absent(root / "_词表.md", LEXICON, "ASR 词表")
    write_if_absent(root / "录音来源" / "_索引.md", INDEX, "来源索引")
    print(
        "\n下一步：\n"
        "  1. 把转写稿（.md/.txt/docx 解析文本）放进 录音来源/\n"
        "  2. 对 Claude 说：清洗 <转写稿路径> 并整理成知识包\n"
        "  3. 产物会落在 <项目根>/<场次名>_YYYY-MM-DD/，双击 HTML 即开\n"
        "体验示例：双击 skill 目录 example/ 内的示例场 HTML"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
