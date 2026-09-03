# transcript-to-knowledge-pipeline

> 把一份对话类录音转写稿，清洗成 **9 模块结构化知识包 + 三层阅读结构 HTML** 的 Claude Code skill。

## 这是什么

一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill，把对话类录音转写稿（飞书妙记 / 得到大脑 / 腾讯会议 / Whisper / 手工整理稿）经过**严格的说话人映射 + 逐回合清洗**，产出 9 个结构化模块和一个双击即开、可搜索、可分享的 HTML 网页。

适合：会议录音、访谈、圆桌、咨询、直播、闲聊的转写整理与知识沉淀。

## 特性（v2.3）

- 🎯 **说话人映射零误判**：角色指纹 + 时间线 + 二次确认，覆盖 8 类陷阱（称呼≠身份 / 账号名≠本人 / 多人压一标签按时段切分 / 双身份标签 / 视频原声误归 / 会后混录 / 旁听无标签 / 用户首认不绝对）
- 📝 **逐回合还原**：忠实对话流（150–700 回合/场），金句原话一字不改，`verify_quotes.py` 引文逐字核证（时间戳命中 + 子串校验 + 敷衍反方检测）
- 📚 **三层阅读结构**：① 执行摘要（10 秒决策）→ ② 全文总结（机器编译，条目带下潜锚点链接）→ ③ 完整模块——「看完①就够请直接关闭」的按需下潜设计
- 🗺️ **结构件图形化**：ASCII 分层图→彩色层带卡、→ 链路→节点胶囊流（节点可点击下潜）；圈号①-⑳ 全文可点段链接
- 🧹 **ASR 订正**：对照表 + `[ASR/存疑]` 标注 + 双源场次对齐，不臆造；英文场/特长场边缘规范
- 📦 **9 模块知识包 + 六档产出**：极轻/轻/轻加强/专项/标准/重装，按决策密度×外部受众×资产含量分档
- 🤖 **批量清洗模式**：flash 子代理流水线（输出纪律模板 + 主对话逐场质检），参考 `references/09`
- ✅ **8 项发布前必查**：`pipeline_check.sh` 一键（含三层收敛与收尾三问）+ 渲染自检（锚点有效性/字数/回归护栏）
- 🗂️ **跨场全局层**：`extract_atoms.py`（递归扫描）抽取原子，`render_views.py` 出脱敏分享版
- 🔌 **零依赖**：单 skill 自包含，python3 标准库即可

## 快速安装

```bash
git clone https://github.com/guoleiycyc-sketch/transcript-to-knowledge-pipeline.git \
  ~/.claude/skills/transcript-to-knowledge-pipeline
```

> 前置：Claude Code + python3（3.6+，无需 pip install）。装完重启 Claude Code。用法与产物结构见 [`INSTALL.md`](./INSTALL.md)，变更史见 [`CHANGELOG.md`](./CHANGELOG.md)。

## 致谢

HTML 渲染器与产物结构源自 `recording-knowledge-pack` 蓝本，已内联至本 skill。
