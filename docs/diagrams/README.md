# 图表索引

本目录保存项目讨论、设计、实现和总结中产生的全部流程图与架构图。

| 编号 | 源文件 | 说明 |
|---|---|---|
| 01 | `01-project-roadmap.mmd` | 从项目 Brief 到最终文档的完整路线 |
| 02 | `02-feature-iteration-loop.mmd` | 每项功能的最小实现与验收循环 |
| 03 | `03-system-architecture.mmd` | React、FastAPI、核心服务和数据层关系 |
| 04 | `04-chat-message-sequence.mmd` | 一次学生消息的端到端时序 |
| 05 | `05-vibe-coding-loop.mmd` | 人与 AI 协作的完整开发循环 |
| 06 | `06-prompt-composition.mmd` | 模块化产品 Prompt 的组合方式 |
| 07 | `07-testing-pipeline.mmd` | AI 产品的五层测试结构 |
| 08 | `08-phase-02a-architecture.mmd` | Phase 02A 的 Router、Service、领域核心和适配器边界 |
| 09 | `09-phase-02a-api-and-data.mmd` | Phase 02A 的公开/受保护 API 与内存实体关系 |
| 10 | `10-phase-02a-chat-transaction.mmd` | 一轮聊天的评估、教学、重试与原子提交时序 |

`rendered/` 保存适合 GitHub README、报告和演示使用的 SVG。任何图表变更都应同时更新源文件、渲染文件和本索引。

本机渲染时，Mermaid CLI 使用 `puppeteer-config.json` 指向已安装的 Google Chrome，避免额外下载浏览器运行包。

渲染器安装在被 Git 忽略的 `.local-tools/` 中；仓库只提交可复现配置、Mermaid 源文件和最终 SVG。
