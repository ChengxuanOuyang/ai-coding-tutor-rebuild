# AI Coding Tutor Rebuild

这是一个教学型复刻项目：从空仓库开始，完整经历 AI 产品的需求分析、教学设计、
Prompt 设计、软件实现、测试、部署、用户评估和项目总结。

本项目不会直接复制现有 AI Coding Tutor 的代码。每个功能都按照“规格、代码、测试、
文档、Git 提交”五项产物推进，以便学习如何使用 AI 构建可解释、可验证、可维护的产品。

## 当前阶段

Phase 01 的教学规则核心、模块化产品 Prompt、可替换 Provider 边界和 Mock CLI 已完成；
最终学习验收与阶段收尾尚未完成。当前版本不调用真实 LLM，也不包含 Web API、数据库或前端。

- [正式设计规格](docs/superpowers/specs/2026-08-10-ai-coding-tutor-rebuild-design.md)
- [Phase 01 实施计划](docs/superpowers/plans/2026-08-10-pedagogy-core-cli.md)
- [教学框架](docs/04-pedagogy-framework.md)
- [产品 Prompt 设计](docs/06-prompt-design.md)
- [开发 Prompt 与复盘](docs/prompts/development/phase-01-pedagogy-core.md)
- [流程图与架构图索引](docs/diagrams/README.md)

## 已实现能力

- 分别计算编程与数学提示等级。
- 新问题逐步提示，同一问题逐级增加帮助。
- 使用提示加权 EMA 更新学生有效能力。
- 严格校验 LLM 教学元数据并执行保守降级。
- 组合角色、教学规则、学生状态、上下文和安全边界。
- 转义并限制用户、Notebook、代码和错误上下文。
- 通过统一 Provider 合同隔离具体模型厂商。
- 使用确定性 Mock Provider 离线运行完整流程。
- 从命令行输出可解析的 Tutor JSON 载荷。

## 快速体验

需要 Python 3.11 或更高版本。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest backend/tests -v
.venv/bin/python -m backend.app.cli \
  --message "Why does my loop not stop?" \
  --programming-level 2 \
  --maths-level 3 \
  --programming-difficulty 4 \
  --maths-difficulty 2
```

示例输出中的 `provider` 应为 `mock`，编程提示等级为 `3`，数学提示等级为 `1`。
Mock 内容是固定的测试响应，不代表真实模型的教学质量。

## 当前结构

```text
backend/
├── app/
│   ├── ai/
│   │   ├── types.py
│   │   ├── pedagogy.py
│   │   ├── prompt_builder.py
│   │   ├── provider.py
│   │   └── mock_provider.py
│   └── cli.py
└── tests/
docs/
├── diagrams/
├── prompts/development/
└── superpowers/
```

## 项目原则

1. Teach, don't solve。
2. 教学逻辑与语言模型调用分离。
3. 人负责目标、边界、判断和验收；AI 负责加速分析与实现。
4. 每次只实现一个可独立验收的小任务。
5. 没有测试和文档的功能不算完成。
6. 不把示例、推测或未运行的评测写成已验证事实。

## 后续阶段

Phase 01 验收后，将依次规划 FastAPI、PostgreSQL、用户与会话、真实 LLM Provider、
React 聊天界面、Notebook 上下文、流式响应、Docker、CI/CD 和用户评估。
