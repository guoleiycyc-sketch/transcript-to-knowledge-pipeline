# transcript-to-knowledge-pipeline

> 把一份对话类录音转写稿，清洗成 **9 模块结构化知识包 + 自包含可搜索 HTML** 的 Claude Code skill。

## 这是什么

一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill，把对话类录音转写稿（飞书妙记 / 得到大脑 / 腾讯会议 / Whisper / 手工整理稿）经过**严格的说话人映射 + 逐回合清洗**，产出 9 个结构化模块和一个双击即开、可搜索、可分享的 HTML 网页。

适合：会议录音、访谈、圆桌、咨询、直播、闲聊的转写整理与知识沉淀。

## 特性

- 🎯 **说话人映射零误判**：角色指纹 + 时间线 + 二次确认方法论，覆盖三种陷阱（称呼≠身份 / 账号名≠本人 / 用户首认不绝对）
- 📝 **逐回合还原**：忠实对话流（150–700 回合/场），金句原话一字不改
- 🧹 **ASR 订正**：对照表 + `[ASR/存疑]` 标注 + 多源场次双源字段，不臆造
- 📦 **9 模块知识包**：执行摘要 / 清洗稿 / 主题整理 / 方法论 / 术语 / 人物卡 / 数据 / 议题地图 / 洞察卡 / 行动清单
- 🌐 **自包含 HTML**：CSS/JS 全内联，离线可用，可分享
- ✅ **6+1 次发布前必查**：一键脚本 `pipeline_check.sh` 跑场内 6 项 + 跨会话 1 项
- 🗂️ **跨场全局层**：`_全局资产/` 累积引语库 / 方法论总库 / 干系人档案，`render_views.py` 可出**脱敏分享版** HTML
- 🔌 **零依赖**：单 skill 自包含（HTML 渲染器已内联），只需 python3 标准库

## 快速安装

```bash
git clone https://github.com/guoleiycyc-sketch/transcript-to-knowledge-pipeline.git \
  ~/.claude/skills/transcript-to-knowledge-pipeline
```

> 前置：[Claude Code](https://docs.anthropic.com/en/docs/claude-code) + python3（3.6+，系统自带，**无需 pip install**）。装完重启 Claude Code。

## 用法

在 Claude Code 里给它转写稿路径：

```
帮我清洗这个录音转写并整理成知识包：/path/to/xxx转写.md
```

Claude 会自动触发本 skill。详见 [`INSTALL.md`](./INSTALL.md)。

## 产物结构

```
<录音项目根>/
  ├─ <场次名>_YYYY-MM-DD/
  │    ├─ 00_执行摘要.md       # BLUF 四段式 ≤200 字（每场最先写）
  │    ├─ 01_清洗稿.md          # 逐回合还原（HTML 时间戳跳转源头）
  │    ├─ 02_主题整理/          # 按议题切段（描述性编码，金句引用制）
  │    ├─ 03_方法论清单.md      # 「遇 X→执行 Y」型，只收本场新增
  │    ├─ 04_术语表.md          # 纯外部名词索引
  │    ├─ 05_人物角色卡.md
  │    ├─ 06_关键数据速查.md    # 可排序表格
  │    ├─ 07_议题关联地图.md    # 母题 + ASCII 分层图（只画本场）
  │    ├─ 08_洞察卡片.md        # 反直觉洞察（必含反方）
  │    ├─ 09_行动清单.md        # 上期回顾 + 带 Owner/状态
  │    ├─ README.md
  │    └─ index.html            # 双击即开，主交付物
  └─ _全局资产/                 # 跨场累积：引语库/方法论总库/干系人档案/母题总图
```

## 本 skill 结构

```
transcript-to-knowledge-pipeline/
  ├─ SKILL.md                  # 入口（Claude 读这个）
  ├─ INSTALL.md                # 安装说明
  ├─ references/01–08.md       # 管线文档（清洗/9模块/检查/pitfalls/跨会话同步）
  ├─ references/format-templates.md + build-html-guide.md  # 内联模板
  └─ scripts/
       ├─ render_pack.py           # 生成单场 index.html（入口）
       ├─ build_html.py            # 渲染器母版（CSS/JS/通用渲染）
       ├─ pipeline_check.sh        # 一键发布前必查 6+1 项
       ├─ extract_atoms.py         # 跨场抽取原子 → _全局资产/
       └─ render_views.py          # 全局视图（methods/quotes/share 脱敏版）
```

## 致谢

HTML 渲染器与产物结构源自 `recording-knowledge-pack` 蓝本，已内联至本 skill，单 skill 独立运行。
