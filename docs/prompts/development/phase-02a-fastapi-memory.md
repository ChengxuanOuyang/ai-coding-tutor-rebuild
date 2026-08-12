# Phase 02A 开发 Prompt 存档

本文件保存 Phase 02A 设计阶段使用的决策、Prompt 模式和校正。实现阶段继续在同一文件追加实际
Prompt、红灯证据、修改原因和验收结果。

书面规格于 2026-08-12 获得学习者批准；随后进入逐任务实现计划，不提前编写产品代码。

## 1. 已批准的选择

| 编号 | 选择 | 内容 |
| --- | --- | --- |
| A | A | FastAPI 与 PostgreSQL 拆成 02A/02B |
| A3 | A3 | 02A 包含注册、登录与受保护聊天 |
| B | B1 | 随机 Bearer Token |
| C | C2 | Mock 默认，同时提供真实模型路径 |
| D | D1 | OpenAI API |
| E | E2 | 教学质量与成本平衡 |
| F | F3 | 瞬时错误重试一次，再失败则明确报错 |
| G | G3 | LLM 自动评估题目元数据 |
| H | H2 | Luna 负责评估，Terra 负责导师回答 |
| I | I1 | 注册时必须填写双自评等级 |
| 架构 | 方案 1 | Router + Service + Repository |

## 2. 只读探索 Prompt

```text
阅读当前 FastAPI 项目设计、Phase 01 教学核心、User/ChatSession 要求和现有测试规范。
只列出 Phase 02A 的目标、边界、依赖、风险和需要澄清的假设，不修改任何文件。
明确哪些职责属于 Router、Service、Domain、Repository、Analyzer 和 Tutor Provider。
指出哪些内容必须推迟到 PostgreSQL 阶段，避免提前耦合 ORM。
```

这个模式先让 AI 建立仓库事实，再讨论方案。它不能直接生成代码，也不能把总产品范围一次塞进单个
阶段。

## 3. 数据模型设计 Prompt

```text
为 FastAPI 内存后端设计 User、AuthToken、ChatSession 和 ChatMessage 领域模型。
先阅读现有 StudentState、PedagogyMetadata、TutorRequest/TutorResponse 和迁移规划。
先列出字段、类型、约束、关系、可见性和生命周期，不要修改文件。
说明哪些字段由客户端提供、哪些由后端计算、哪些来自不可信 LLM 输出。
指出你需要确认的假设，并检查设计能否在下一阶段由 PostgreSQL Repository 实现。
```

相比“帮我写四个模型”，这个 Prompt 增加了现有合同、数据来源、信任边界和未来替换要求。

## 4. OpenAI Adapter 设计 Prompt

```text
依据当前 OpenAI 官方文档，为现有 Provider Protocol 设计 Responses API Adapter。
不要先写实现。先给出请求映射、响应映射、结构化 Analyzer Schema、Token 用量、超时、
可重试错误、不可重试错误、配置项和秘密管理边界。
Mock 必须继续作为默认自动测试路径；真实网络测试必须显式启用。
不得把 API Key、完整 Prompt 或 Bearer Token 写入代码、日志、测试快照或 Git。
```

该模式要求先取得官方证据，再设计适配层；模型名必须可配置，不能凭记忆硬编码为永久默认。

## 5. 原子聊天服务 Prompt

```text
设计 ChatService 的单轮聊天事务，不修改文件。
按顺序说明鉴权、所有权、历史读取、Analyzer、Schema 校验、教学计算、Prompt Builder、
Tutor Provider 和最终提交。
对每个可能失败的边界说明 HTTP 错误、是否重试、是否保存消息、是否更新能力值。
核心不变量：整轮成功前不得提交用户消息、助手消息或学生状态更新。
```

该模式把“能聊天”转换为可测试的不变量，防止 AI 只实现成功路径。

## 6. TDD 实现 Prompt 模板

```text
实现 Phase 02A 的一个最小任务：[单一任务名称]。
先读取规格与相关现有代码，只修改任务列出的文件。
先写能被正常收集、且因缺少目标行为而失败的测试；展示红灯原因。
再写满足测试的最小实现，运行目标测试、相关回归测试和 Ruff。
不要提前实现后续任务，不访问真实 OpenAI，不修改 main。
完成后总结测试证据、剩余风险，并把本轮 Prompt 和校正追加到阶段存档。
```

模板中的 `[单一任务名称]` 由后续实现计划中的具体任务替换。每个任务必须有自己的文件范围和验收
命令，不能用“整个后端”作为任务名。

## 7. 设计阶段校正记录

| 观察 | 校正 |
| --- | --- |
| 最初只讨论三个 Analyzer 字段 | 现有 `PedagogyMetadata` 还要求 `is_elaboration`，正式合同保留四字段 |
| 用户选择 LLM 自动评估 | LLM 只提供不可信评估；后端 Schema 和 Pedagogy Engine 保留最终控制权 |
| 用户选择真实 OpenAI | 自动测试仍使用 Mock，真实冒烟测试必须显式启用 |
| 可考虑模型失败时切 Mock | 拒绝静默回退，避免固定测试文本被误认为真实导师回答 |
| Python 3.11 基线测试段错误 | 复现到本机 `readline`，改用已验证 Python 3.12，不归因于项目代码 |

## 8. 官方资料

- [OpenAI Text generation](https://developers.openai.com/api/docs/guides/text)
- [OpenAI Developer quickstart](https://developers.openai.com/api/docs/quickstart)
- [OpenAI Model guidance](https://developers.openai.com/api/docs/guides/latest-model)

访问日期：2026-08-11。
