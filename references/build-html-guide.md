# HTML 组装指南

`render_pack.py` 是一键生成 HTML 的通用 wrapper。它读一个场次目录里的 01-09 md，自动提取配置，调母版渲染器（`build_html.py`）生成自包含的 `index.html`。

## 一键生成

```bash
python <skill路径>/scripts/render_pack.py <场次目录> [--brand "显示名"]
```

- 不带 `--brand`：用场次目录名作标题。
- 输出 `<场次目录>/index.html`，自包含（CSS/JS 全内联），双击即开。
- 终端会打印提取到的段数/人数/洞察数/方法论数/术语数/是否有战略诊断，方便核对。

例：
```bash
python ~/.claude/skills/transcript-to-knowledge-pipeline/scripts/render_pack.py \
  ~/Desktop/某项目/某某讨论_2026-08-10 --brand "某某讨论"
```

## render_pack 自动提取了什么（无需手写配置）

| 项 | 来源 |
|---|---|
| 段标题 / 副标题 | 02/第N段 的 `# 第N段 · 标题` + `> 时段：` |
| 人物 / 发言量 / 一句话标签 | 05 的 `## 人名` + `约 XX%` + `**背景与立场**：` |
| 母题（总览页用） | 07 的 `**母题**：` |
| 洞察卡数 | 08 的 `^## 卡 \d+` |
| 方法论卡数 | 03 的 `^## \d+\.` |
| 术语条数 | 04 的 `^### ` |
| 人物数 | 05 的 `## 人名` |
| 是否有战略诊断 | 09 文件是否存在 |
| 侧栏导航 / 段名 / 各模块计数 | 全部自动生成 |

所以只要 md 按规范写（见 `format-templates.md`），就零配置出 HTML。

## 定制总览页（可选）

默认总览页是自动生成的骨架（母题 + 发言者 + 分段目录 + 导航提示）。想要更丰富的总览（背景、与上一场的关系、贯穿主题……），写一个 `00_总览.md`：

```markdown
# 总览 · 这一场在讲什么

（自由发挥：这是什么、几个人、母题、分段一句话目录、贯穿主题、与同体系其他场的关系……）
```

有 `00_总览.md` 时，render_pack 用它的内容作总览页（目前默认行为是自动骨架；若要读 00，可在 render_pack 里把 overview 切换为读 00_总览.md）。

## 深度定制（改母版）

`render_pack.py` 走"通用渲染"路线：议题地图、洞察地图用 md 原文（含 ASCII 代码块）直接渲染，不画内容特定的花式可视化。这是为了**通用性**（任何场次零配置）。

如果某一场你想要**内容特定的花式可视化**（比如手画的三层信息图、维度泳道、数据量级条），有两条路：

1. **改这一场的产物**：在场次目录里放一个自己的 `build_html.py`，按 monkey-patch 模式调母版（参考 `render_pack.py` 的写法），覆盖 `render_map` / `render_insight_map` / `render_data` 等为这一场定制版。这是"一场一定制"。
2. **改母版**：直接编辑 `scripts/build_html.py`（影响所有场次）。除非有普适的改进，否则不推荐。

日常用法就是 `render_pack.py` 一键出 HTML；只有要花式可视化时才下场自己写。

## 已知坑

1. **金句格式必须对**：`**【姓名】** [ts] 原话`。错了就丢交互（金句变普通文字）。这是最高频的坑。
2. **母版 `render_method` 标题写死了"Harry 方法论清单"**：render_pack 已自动 replace 成 `<brand> 方法论清单`，无需处理。若直接用母版（不走 render_pack），要自己 replace。
3. **ASCII 图必须用 ``` ``` 代码块**：议题地图、洞察地图里的图，不用代码块会被当普通段落、渲染错乱。
4. **`render_insights` 的 `_DIM` 维度标题**：母版写死了首场的维度名。render_pack 的 `render_insights_generic` 已绕过它（不显示维度小标题），无需处理。
5. **大文件**：母版 `build_html.py` 约 2400 行（含完整 CSS/JS）。一般不用读它，遇到渲染问题再 grep 定位。
6. **金句"跳清洗稿"默认无效**：金句卡的时间戳点击本应跳到清洗稿对应行，但 render_pack 默认**不把 01 清洗稿渲染进 HTML**（避免文件过大），所以跳转目标不存在——点击无反应，但**复制功能正常**。三场实际产出也都是这样（清洗稿独立成 md，不进网页）。若要让某场启用跳转，需额外把清洗稿渲染成一个折叠的 transcript section（render_pack 默认不做）。

## 验证清单（生成后自检）

```bash
# section 齐全
grep -o 'id="[a-z0-9]*"' <场次>/index.html | grep -E 'overview|people|map|insights|method|seg[0-9]|glossary|data' | sort -u
# 各类卡片数
grep -c 'class="card method-card insight-card"' <场次>/index.html   # 洞察
grep -c 'class="card method-card"' <场次>/index.html                 # 方法论
grep -c 'glossary-card"' <场次>/index.html                           # 术语
grep -c 'people-card"' <场次>/index.html                             # 人物
# ASCII 图渲染
grep -c 'class="ascii-map"' <场次>/index.html                        # 议题/洞察地图
# 无残留首场标题
grep -c 'Harry 方法论清单' <场次>/index.html                          # 应为 0
```

section 数 = 6（固定：overview/people/map/insights/method/glossary/data）+ 段数 +（有 09 则 +1）。卡片数应和 md 里的标题数一致。
