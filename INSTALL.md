# 安装与使用说明（给接收方）

这是一个 **Claude Code skill**，能把一份对话类录音转写稿（飞书妙记 / 得到大脑 / 腾讯会议 / Whisper / 手工稿），经过严格的说话人映射和清洗，产出 **9 模块结构化知识包 + 一个自包含、可搜索、可分享的 HTML 网页**。

**单 skill 自包含**——HTML 渲染器（`scripts/build_html.py` + `render_pack.py`）和格式模板都已内联，**不依赖任何其他 skill**。

---

## 一、前置条件
1. **Claude Code**（CLI / 桌面 App / IDE 插件，需支持 skills 的版本）
2. **python3**（3.6+）——macOS / Linux 自带，Windows 需自行装。**零第三方库依赖**，只用 Python 标准库。

检查：`python3 --version`

## 二、安装（只需一个目录）
解压后，把 `transcript-to-knowledge-pipeline` 目录放到：
- **用户级**（所有项目可用，推荐）：`~/.claude/skills/transcript-to-knowledge-pipeline/`
- 或**项目级**：`<项目根>/.claude/skills/transcript-to-knowledge-pipeline/`

装完**重启 Claude Code**，让它扫描到新 skill。

## 三、怎么用
在 Claude Code 里给它转写稿路径，自然语言触发：
> 帮我清洗这个录音转写并整理成知识包：`/path/to/xxx转写.md`

也可显式说「用 transcript-to-knowledge-pipeline」。

## 四、使用须知（重要）
1. **说话人映射是最高风险环节**：skill 会在清洗前要求你确认每个 ASR 标签对应谁，绝不能凭「被怎么称呼」判定身份，必须用「角色指纹 + 时间线 + 你二次确认」。
2. **金句原话一字不改**，ASR 听不准的标 `[ASR/存疑]`，不臆造。
3. 默认**逐回合还原**（一场 150–700 回合），忠实优先于简洁。
4. 产物落在 `<场次名>_YYYY-MM-DD/` 子目录，含 `00_执行摘要.md`、`01_清洗稿.md` … `09_行动清单.md` + `<场次名>.html`。双击 HTML 即开（CSS/JS 全内联，可离线、可发给别人）。
5. 每次交付前 skill 会自动跑**质量门禁**（说话人一致性 / ASR 残留 / 金句格式 / 结构 / HTML / README，一键 `pipeline_check.sh`）+ 引文核证（`verify_quotes.py`）。

## 五、装完自检
```bash
python3 ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/selftest.py
# ✓ selftest 通过（md 契约 → 渲染 → 引文核证 全链绿灯）
```
想先看成品长什么样：双击 `example/示例场_SaaS定价讨论_2026-01-15/` 里的 HTML（虚构内容的完整演示场）。

新项目建议先初始化骨架（config + ASR 词表 + 来源索引）：
```bash
python3 ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/init_project.py <你的项目根> [--delegation]
```

## 六、结构
```
transcript-to-knowledge-pipeline/
  ├─ SKILL.md                         ← 入口（Claude 读这个）
  ├─ INSTALL.md                       ← 本文件
  ├─ CHANGELOG.md                     ← 变更史
  ├─ LICENSE                          ← MIT
  ├─ example/示例场_SaaS定价讨论_2026-01-15/   ← 完整演示场（双击 HTML 体验）
  ├─ references/
  │    ├─ 01-intake-speaker-mapping.md   ← Intake + 说话人映射（含可选先验名单）
  │    ├─ 02-cleansing-asr.md            ← 清洗 + ASR 订正
  │    ├─ 03-modules-and-templates.md    ← 9 模块格式契约与模板
  │    ├─ 04-html-rendering.md           ← HTML 组装（含 --share 分享版）
  │    ├─ 05-quality-gates.md            ← 发布前质量门禁
  │    ├─ 06-pitfalls.md                 ← 坑库（按阶段归类）
  │    ├─ 07-multi-session-kb.md         ← 多场次知识库同步
  │    └─ 08-subagent-modes.md           ← 子代理模式（批量/委派）
  └─ scripts/
       ├─ render_pack.py            ← 生成 HTML（入口；--share 出脱敏分享版）
       ├─ build_html.py             ← 渲染器母版（CSS/JS/通用渲染）
       ├─ verify_quotes.py          ← 引文逐字/时间戳核证
       ├─ init_project.py           ← 新项目骨架初始化（config+词表+索引）
       ├─ selftest.py               ← 端到端自检（装机验证/改动回归）
       ├─ diff_report.py            ← 清洗忠实度审计（原稿 vs 清洗稿）
       ├─ extract_atoms.py          ← 原子知识抽取（多场次）
       └─ render_views.py           ← 跨场视图（含脱敏分享版）
```

有问题找分享给你的人。祝用得顺手。
