# transcript-to-knowledge-pipeline

> 把一份对话类录音转写稿，清洗成 **9 模块结构化知识包 + 自包含可搜索 HTML** 的 Claude Code skill。

## 这是什么

一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill，把对话类录音转写稿（飞书妙记 / 得到大脑 / 腾讯会议 / Whisper / 手工整理稿）经过**严格的说话人映射 + 逐回合清洗**，产出 9 个结构化模块和一个双击即开、可搜索、可分享的 HTML 网页。

适合：会议录音、访谈、圆桌、咨询、直播、闲聊的转写整理与知识沉淀。

## 特性

- 🎯 **说话人映射零误判**：角色指纹 + 时间线 + 二次确认方法论，把 ASR 标签准确还原为人
- 📝 **逐回合还原**：忠实对话流（150–700 回合/场），金句原话一字不改
- 🧹 **ASR 订正**：对照表 + `[ASR/存疑]` 标注，不臆造
- 📦 **9 模块知识包**：清洗稿 / 主题整理 / 方法论 / 术语 / 人物卡 / 数据 / 议题地图 / 洞察卡 / 战略诊断
- 🌐 **自包含 HTML**：CSS/JS 全内联，离线可用，可分享
- ✅ **6 次发布前必查**：说话人 / ASR / 金句格式 / 结构 / HTML / README
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
<场次名>_YYYY-MM-DD/
  ├─ 01_清洗稿.md          # 逐回合还原（HTML 时间戳跳转源头）
  ├─ 02_主题整理/          # 按议题切段
  ├─ 03_方法论清单.md      # 可复用思维工具
  ├─ 04_术语表.md
  ├─ 05_人物角色卡.md
  ├─ 06_关键数据速查.md    # 可排序表格
  ├─ 07_议题关联地图.md    # 母题 + ASCII 分层图
  ├─ 08_洞察卡片.md        # 反直觉洞察（含反方）
  ├─ 09_战略诊断与行动清单.md
  ├─ README.md
  └─ index.html            # 双击即开，主交付物
```

## 本 skill 结构

```
transcript-to-knowledge-pipeline/
  ├─ SKILL.md                  # 入口（Claude 读这个）
  ├─ INSTALL.md                # 安装说明
  ├─ references/01–07.md       # 管线文档（清洗/9模块/检查/pitfalls）
  ├─ references/format-templates.md + build-html-guide.md  # 内联模板
  └─ scripts/render_pack.py + build_html.py                # 内联 HTML 渲染器
```

## 致谢

HTML 渲染器与产物结构源自 `recording-knowledge-pack` 蓝本，已内联至本 skill，单 skill 独立运行。
