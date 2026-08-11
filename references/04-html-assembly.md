# 阶段 ④ HTML 组装

## 一条命令出 HTML

```bash
python ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/render_pack.py <场次目录>
# 可选：python ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/render_pack.py <场次目录> --brand "显示名"
```

**不要试图手写 HTML**——`render_pack.py` 自动从 md 文件提取：

- 段标题（从 02 的 `# 第N段 · `）
- 人物（从 05 的 `## 人名` + `**背景与立场**：` + `约 XX%`）
- 母题（从 07 的 `**母题**：`）
- 各类计数

生成 `index.html`（自包含 CSS/JS 内联，双击即开）。

---

## 渲染器依赖的标记（必准）

详见 `references/03` 和 `references/06` 的陷阱表。最关键的几个：

### 金句格式（缺一不可）

```markdown
**【姓名】** [MM:SS 或 HH:MM:SS] 原话
```

→ 渲染为可点击金句卡（跳清洗稿 + 复制）

### 段标题格式

```markdown
# 第1段 · AI agent 定价分层
```

→ render_pack 提取为侧边栏导航

### 人物卡标记

```markdown
## 王伟
**角色标签**：…
**背景与立场**：…
**发言量占比**：约 30%
```

→ 渲染为人物卡 + 进度条

### 议题地图（必须代码块）

```markdown
\`\`\`
第一层…
\`\`\`
```

→ 渲染为等宽图

---

## 已知坑（HTML 渲染相关）

完整坑列表见 `references/06-pitfalls.md`。HTML 渲染特有的：

| 坑 | 原因 |
|---|---|
| 金句全是普通文字 | 漏 `】` 或时间戳格式错 |
| 侧边栏段顺序乱 | 02 文件名 N 不连续 |
| 人物卡进度条 0 | 漏写 `约 XX%` |
| 议题地图变成普通段落 | 没包在 ``` 代码块 |
| 洞察卡只有核心、没启示/反方 | 漏字段头（render_pack 不识别） |
| 不带 `--brand` 时标题是目录名 | 想要自定义加 `--brand "..."` |
| 跨场改了一场的 HTML 模板 | 用 monkey-patch 复用首场渲染器，只维护差异 |

详细改造指南（CSS/JS/通用渲染、monkey-patch 复用、`render_meta.py` 等）见 [`build-html-guide.md`](./build-html-guide.md)（已内联至本 skill）。

---

## 跨场复用：monkey-patch 模式

如果跨项目复用（同一知识体系多场），**不要复制粘贴 HTML 生成代码**。而是：

```python
# 伪代码：import build_html as B，然后覆盖差异
import build_html as B

B.SEG_META = "..."  # 覆盖段标题提取
B.PEOPLE_xxx = "..."  # 覆盖人物卡提取
B.render_overview = my_render_overview  # 覆盖总览页渲染
# ... 其他需要差异化的函数

# 自己的 main 读本场 md
if __name__ == "__main__":
    main()
```

坑：原 `render_method`（标题写死"Harry 方法论清单" + 副标题"14 张…卡"）和 `render_insights`（_DIM 维度小标题）是硬编码首场的——要在 `main` 末尾对 `html_out` 做 replace 修正，或重定义这两个函数。

**验证方法**：grep 上一场人名/段名区分"残留 bug" vs "合法跨场呼应内容"。

跨项目复用时 `sys.path` 用绝对路径指向首场 `_工作文件`。

---

## README.md（交付前最后一步）

```markdown
# 场次名 · 知识包

## 怎么看
打开 `index.html`（双击即开，CSS/JS 全内联，无外部依赖）。

左侧导航 / 全文搜索高亮 / 金句点击复制 / 时间戳跳原文 / 表格排序 / 深浅主题。

## 文件说明
| 文件 | 用途 |
|---|---|
| 01_清洗稿.md | 素材层，HTML 时间戳跳转源头 |
| 02_主题整理/ | 按议题切段 |
| … | … |
| index.html | 主交付物 |

## 已知瑕疵
- ASR 错字：[列出 `[ASR/存疑]` 项]
- 说话人识别：<置信度 + 残留未识别项>

## 与同体系其他场的关系
- 本场卡 X = 2026-07-17 场卡 Y
- <跨场呼应清单>
```

---

## 退出本阶段的自检清单

- [ ] `render_pack.py` 运行无错
- [ ] `index.html` 生成（不依赖外部网络）
- [ ] 双击 `index.html` 能开（不是 Mac 上"打开方式"问题）
- [ ] 浏览器里：左侧导航有所有段、人物卡显示、议题地图显示、金句点击可复制
- [ ] README.md 写完（含跨场呼应）
- [ ] 跨场复用：用 monkey-patch，不复制渲染器
- [ ] 第一场模板 vs 新场差异明确记录（避免下次又复制）