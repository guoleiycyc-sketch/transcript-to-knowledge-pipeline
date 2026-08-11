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
4. 产物落在 `<场次名>_YYYY-MM-DD/` 子目录，含 `01_清洗稿.md` … `09_战略诊断.md` + `index.html`。双击 `index.html` 即开（CSS/JS 全内联，可离线、可发给别人）。
5. 每次交付前 skill 会自动跑 **6 次发布前必查**（说话人一致性 / ASR 残留 / 金句格式 / 结构 / HTML / README）。

## 五、装完自检
```bash
ls ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/render_pack.py
ls ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/build_html.py
python3 ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/render_pack.py --help 2>/dev/null || echo "python3 就绪（无 --help 属正常）"
```

## 六、结构
```
transcript-to-knowledge-pipeline/
  ├─ SKILL.md                         ← 入口（Claude 读这个）
  ├─ INSTALL.md                       ← 本文件
  ├─ references/01–07.md              ← 清洗 + 9 模块 + 检查 + pitfalls
  ├─ references/format-templates.md        ┐ 已内联的格式模板
  ├─ references/build-html-guide.md        ┘ 与 HTML 改造指南
  └─ scripts/
       ├─ render_pack.py               ← 生成 index.html（入口）
       └─ build_html.py                ← 渲染器母版（CSS/JS/通用渲染）
```

有问题找分享给你的人。祝用得顺手。
