# Changelog

本项目版本历史。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-08-11

首个公开版本。

### 新增
- **完整工程化管线**：录音转写 → 9 模块知识包 + 自包含 HTML，5 阶段 + 6 次发布前必查
- **说话人映射方法论**：角色指纹 + 时间线 + 用户二次确认，杜绝「凭称呼判定身份」
- **ASR 订正机制**：对照表 + `[ASR/存疑]` 标注，不臆造
- **9 模块产物**：清洗稿 / 主题整理 / 方法论 / 术语 / 人物角色卡 / 关键数据 / 议题关联地图 / 洞察卡片 / 战略诊断
- **自包含 HTML 渲染器**：`scripts/render_pack.py` + `build_html.py`（CSS/JS 全内联，离线可用）
- **逐回合还原**：150–700 回合/场，金句原话一字不改
- **pitfalls 库**：P1–P10 持续累积的踩坑记录

### 特性
- 单 skill 自包含，**无外部 skill 依赖**（HTML 渲染器与格式模板已内联）
- **零第三方 Python 库**（仅用标准库 os/re/html/pathlib/sys）
- 6 次发布前必查：说话人一致性 / ASR 残留 / 金句格式 / 结构完整性 / HTML 渲染 / README
