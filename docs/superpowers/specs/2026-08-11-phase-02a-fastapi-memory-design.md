# Phase 02A：FastAPI 内存后端设计

状态：交互式设计与书面规格均已批准
日期：2026-08-11  
分支：`feature/phase-02a-fastapi-memory`

## 1. 目标

Phase 02A 把 Phase 01 的纯教学核心接入一个可运行的 FastAPI 后端。学生可以注册、登录、创建
教学会话、发送消息和读取历史；服务默认使用确定性的 Mock 实现，也可以显式接入 OpenAI 进行
真实人工验证。

本阶段使用内存 Repository。服务重启后用户、Token、会话和消息都会清空。Phase 02B 再用
PostgreSQL、SQLAlchemy 2.0 和 Alembic 替换存储适配器，不改 Router、Service 或领域合同。

## 2. 已批准的产品决策

| 决策 | 选择 | 理由 |
| --- | --- | --- |
| 阶段范围 | 拆成 02A FastAPI 内存后端与 02B PostgreSQL | 隔离 HTTP 与持久化问题 |
| 最小产品 | 注册、登录、退出、用户资料、会话和聊天 | 练习完整受保护流程 |
| 登录凭证 | 随机 Bearer Token | 比 JWT 和 Cookie 更适合当前无前端、无数据库阶段 |
| Token 存储 | 只保存摘要，默认 24 小时过期 | 避免服务端保存可直接使用的明文 Token |
| 模型通道 | Mock 为默认，OpenAI 为显式配置 | 自动测试离线且确定，人工验证可使用真实模型 |
| OpenAI API | Responses API | 使用当前官方推荐的文本生成接口 |
| 问题评估 | LLM Analyzer + 严格 Schema + 后端教学算法 | 自动化体验不牺牲确定性教学边界 |
| Analyzer 模型 | `gpt-5.6-luna` | 适合高频、结构化、成本敏感的分类工作 |
| Tutor 模型 | `gpt-5.6-terra` | 平衡教学质量与成本 |
| Reasoning effort | `medium` | 作为质量、延迟和成本的初始基线 |
| 上游失败 | 瞬时错误重试一次，仍失败则明确报错 | 不静默伪造 Mock 回答 |
| 自评等级 | 注册时必须提交编程与数学两个 1-5 等级 | 不使用未经学生确认的默认能力 |
| 内部结构 | Router + Service + Repository | Phase 02B 可只替换 Repository Adapter |

模型是否对具体账户开放必须在真实接入时验证。模型名称和 reasoning effort 都由环境变量覆盖，
不属于业务代码常量。

## 3. 范围

### 3.1 本阶段包含

- FastAPI 应用工厂、健康检查和自动 OpenAPI 文档。
- 注册、登录、退出和当前用户资料。
- 密码哈希、随机 Bearer Token、过期检查和当前 Token 撤销。
- 创建/列出教学会话，读取消息历史，发送一轮教学消息。
- 用户、Token、会话和消息的 Repository Protocol 与内存实现。
- 会话所有权校验；不存在和不属于当前用户都返回 404。
- Mock 与 OpenAI 两套 Problem Analyzer 和 Tutor Provider Adapter。
- LLM 评估结果的严格结构校验。
- 一轮聊天的原子提交语义、错误映射和输入限制。
- 单元测试、API 集成测试、Provider 合同测试和可选真实冒烟测试。
- 本地运行、环境变量和 OpenAPI 手工体验说明。

### 3.2 本阶段不包含

- PostgreSQL、SQLAlchemy、Alembic 或任何磁盘持久化。
- React UI、Cookie、JWT、刷新 Token、多因素认证或找回密码。
- 修改个人资料、删除/重命名会话或管理员功能。
- 流式输出、WebSocket、Notebook、附件或 Token 限额。
- 自动模型故障切换，或真实模型失败后静默返回 Mock 内容。

## 4. 架构与职责

### 4.1 接口层

FastAPI Router 只负责 HTTP 协议、Pydantic 请求/响应模型、依赖注入、Bearer Token 提取和领域
错误到 HTTP 状态码的映射。Router 不直接操作字典，不计算提示等级，也不调用 OpenAI SDK。

### 4.2 应用服务

- `AuthService`：注册、登录、退出、Token 解析和用户查询。
- `ChatService`：会话所有权、历史读取和异步聊天回合编排。
- `ChatUnitOfWork`：暂存两条消息与能力更新，只在整轮成功后提交。

Service 依赖 Repository、Analyzer 和 Provider 的 Protocol，不依赖具体适配器。

### 4.3 领域核心

继续复用 Phase 01 的 `compute_hint_levels`、`update_effective_level`、
`coerce_pedagogy_metadata` 和 `build_system_prompt`。LLM 不能直接设置提示等级或有效能力值。

### 4.4 端口与适配器

- Repository Protocol：用户、Token、会话和消息读写合同。
- In-memory Adapter：Phase 02A 的字典存储实现。
- Problem Analyzer Protocol：统一返回经过验证的 `ProblemAssessment`。
- Tutor Provider Protocol：继续返回统一 `TutorResponse`。
- Mock Adapter：默认测试路径。
- OpenAI Adapter：只在显式配置时导入 SDK、读取密钥并调用 Responses API。

## 5. HTTP API 合同

### 5.1 公开接口

| 方法与路径 | 成功状态 | 目的 |
| --- | --- | --- |
| `GET /health` | 200 | 返回服务状态，不调用模型 |
| `POST /auth/register` | 201 | 创建用户，不自动登录 |
| `POST /auth/login` | 200 | 返回 Bearer Token 和过期时间 |

注册请求包含 `email`、`username`、`password`、`self_programming_level` 和
`self_maths_level`。两个等级必须是 1-5 的整数。邮箱去除首尾空白并转为小写后检查唯一性。
用户名保留显示形式，同时用 `casefold()` 生成唯一性键，因此 `Student` 与 `student` 冲突。
密码只进入哈希函数，不进入日志、错误详情或响应。

### 5.2 受保护接口

| 方法与路径 | 成功状态 | 目的 |
| --- | --- | --- |
| `POST /auth/logout` | 204 | 撤销当前 Token |
| `GET /users/me` | 200 | 返回当前用户公开资料和双维度学习状态 |
| `POST /sessions` | 201 | 创建当前用户的教学会话 |
| `GET /sessions` | 200 | 列出当前用户的会话 |
| `GET /sessions/{session_id}/messages` | 200 | 返回按创建时间排序的消息 |
| `POST /sessions/{session_id}/messages` | 201 | 创建一个完整教学回合 |

消息请求只接受学生文本。难度、同题状态和 elaboration 状态由 Analyzer 推断，不允许客户端直接
提交提示等级或有效能力值。响应返回本轮用户/助手消息和会话标识，不返回 Analyzer 评估、双提示
等级、有效能力值或系统 Prompt。`GET /users/me` 只公开双自评等级，不公开双有效等级。

输入上限：邮箱 254 字符；用户名 3-32 字符，且只接受 ASCII 字母、数字、下划线、点和连字符；
密码 12-128 字符；会话标题 120 字符；学生消息去除首尾空白后为 1-4,000 字符。Prompt Builder
只接收最近 10 条消息序列化后的最多 4,000 字符，超出部分按现有截断规则处理。

## 6. 内存数据模型

### 6.1 User

- UUID 主键。
- 规范化邮箱与唯一用户名。
- 现代密码哈希，不保存明文密码。
- 编程/数学自评等级：整数 1-5。
- 编程/数学有效等级：浮点数 1.0-5.0，初始值等于对应自评。
- 当前编程/数学提示等级。
- 创建与更新时间，使用带时区的 UTC 时间。

### 6.2 AuthToken

- Token 摘要，不保存返回给客户端的原始 Token。
- 用户 UUID。
- 创建时间与过期时间。
- 默认有效期 86,400 秒，可通过配置覆盖。

### 6.3 ChatSession

- UUID 主键和用户 UUID。
- 可选标题。
- 创建与更新时间。

### 6.4 ChatMessage

- UUID 主键、会话 UUID、角色、内容和创建时间。
- 用户消息可带 `ProblemAssessment` 与本轮双提示等级。
- 助手消息可带 Provider、模型、输入 Token 和输出 Token。

### 6.5 ProblemAssessment

Analyzer 必须返回四个字段：`programming_difficulty`、`maths_difficulty`、`same_problem` 和
`is_elaboration`。两个难度必须是整数 1-5，两个标志必须是布尔值。第一轮必须由后端强制改为
`same_problem=false`、`is_elaboration=false`；`same_problem=false` 时也强制
`is_elaboration=false`。

## 7. 一轮聊天的数据流

1. Router 验证请求格式并解析当前 Bearer Token。
2. `ChatService` 获取该会话的异步锁，验证会话存在且属于当前用户，并读取受长度限制的最近历史。
3. Problem Analyzer 根据学生消息与最近历史返回结构化评估。
4. 后端先做严格 Schema 校验，再调用现有 metadata coercion 施加跨字段不变量。
5. Pedagogy Engine 计算编程/数学提示等级，并在临时状态上计算 EMA。
6. Prompt Builder 组合教学规则、临时状态、学生消息和受限历史。
7. Tutor Provider 生成统一 `TutorResponse`。
8. Unit of Work 一次性提交用户消息、助手消息和新学生状态。
9. Router 返回两条学生可见消息和会话标识；隐藏评估、提示等级、内部有效等级和系统 Prompt。

如果步骤 3-7 任一步失败，步骤 8 不执行：不保存半个回合，也不更新能力值。

每个会话使用独立 `asyncio.Lock` 串行处理聊天回合，外部模型调用期间也保持该会话锁；不同会话
仍可并发。这样 02A 不会因两个同时请求读取同一旧状态而丢失提示升级或 EMA 更新。Repository
Protocol 使用异步方法，为 02B 的数据库适配器保留一致调用形态。

## 8. OpenAI 接入设计

官方文档要求 API Key 从环境变量读取；官方 SDK 会读取 `OPENAI_API_KEY`。文本生成使用
Responses API，产品 Prompt 放入 `instructions`，学生输入放入 `input`，文本使用 SDK 提供的
聚合输出字段而不是假设固定的底层数组位置。

配置项：

- `APP_PROVIDER_MODE=mock|openai`，默认 `mock`。
- `OPENAI_API_KEY`，仅在 `openai` 模式必需。
- `OPENAI_ANALYZER_MODEL`，默认 `gpt-5.6-luna`。
- `OPENAI_TUTOR_MODEL`，默认 `gpt-5.6-terra`。
- `OPENAI_REASONING_EFFORT`，默认 `medium`。
- `OPENAI_TIMEOUT_SECONDS`，使用有限正数默认值。
- `AUTH_TOKEN_TTL_SECONDS=86400`。

Analyzer 使用 Structured Outputs 或 SDK 的等价结构化解析能力产生严格 Schema。Tutor 调用使用
现有版本化 Prompt。自动测试不能要求 `OPENAI_API_KEY`，真实冒烟测试必须显式启用。

官方来源（访问于 2026-08-11）：

- [Text generation](https://developers.openai.com/api/docs/guides/text)
- [Developer quickstart](https://developers.openai.com/api/docs/quickstart)
- [Model guidance](https://developers.openai.com/api/docs/guides/latest-model)

## 9. 重试、错误和安全

### 9.1 重试

只对连接失败、超时、限流和上游 5xx 等瞬时故障重试一次，默认退避 0.25 秒。API Key 错误、
请求错误和 Schema 错误不重试。测试注入无等待策略，不能真的休眠。

### 9.2 HTTP 错误映射

| 状态 | 语义 |
| --- | --- |
| 401 | Token 缺失、无效或过期 |
| 404 | 会话不存在或不属于当前用户 |
| 409 | 规范化邮箱或用户名已存在 |
| 422 | 客户端字段、等级或长度不合法 |
| 502 | 上游返回无法通过结构校验的内容 |
| 503 | 瞬时上游故障重试一次后仍失败 |
| 500 | 未预期内部错误，响应不暴露堆栈或秘密 |

错误响应统一为 `{"error": {"code": "stable_code", "message": "safe message"}}`。自动测试依赖
稳定 `code`，不依赖可能调整的完整英文文案。

### 9.3 安全边界

- 密码使用 Argon2id 等现代密码哈希实现。
- Bearer Token 使用密码学安全随机数生成，只保存摘要，并使用常量时间比较。
- API Key、密码、Bearer Token、完整系统 Prompt 不进入日志或 Git。
- 所有用户文本和历史继续作为不可信 Prompt 内容包裹。
- 请求体、用户名、邮箱、密码、单条消息和历史上下文都有明确长度上限。
- 跨用户资源统一返回 404，避免泄露其他用户的会话是否存在。

## 10. 测试策略

### 10.1 单元测试

- 密码哈希与校验、Token 创建/过期/撤销。
- 各 Repository 的唯一约束、所有权和排序。
- Auth/Chat Service 正常、边界与失败路径。
- Analyzer Schema、第一轮强制规则和 Provider 错误映射。
- 聊天失败时不保存消息、不更新学生状态。
- 继续运行 Phase 01 的全部教学核心测试。

### 10.2 API 集成测试

使用 FastAPI TestClient、内存 Repository 和 Mock Analyzer/Tutor 覆盖：注册到聊天的完整路径、
所有状态码、Token 过期、跨用户访问、重复注册、消息排序和 OpenAPI schema。

### 10.3 Provider 合同与真实冒烟测试

Mock 与 OpenAI Adapter 都必须满足相同领域合同。默认套件不访问网络。真实 OpenAI 冒烟测试只有
在显式开关和 API Key 同时存在时运行，并且不把模型文本内容作为精确字符串断言。

## 11. 验收标准

- 新环境不配置 API Key 也能启动服务并完成 Mock 全链路。
- `/docs` 中可以手工完成注册、登录、创建会话、发送消息和读取历史。
- 自动测试证明跨用户读取被拒绝、Token 可撤销且会过期。
- 自动测试证明 Analyzer/Tutor 任一失败都不会留下部分状态。
- Mock 模式相同输入得到可重复的结构和教学结果。
- OpenAI 模式缺少密钥时启动失败并给出不泄密的明确配置错误。
- 显式真实冒烟测试能分别观察 Analyzer 模型和 Tutor 模型名称及 Token 用量。
- 所有新增代码通过 Pytest、Ruff 和秘密扫描。
- 规格、Prompt 记录、Mermaid 源图和 SVG 渲染与代码一起受版本控制。

## 12. 实施边界与 Phase 02B 交接

Phase 02A 的 Repository Protocol 必须能由 PostgreSQL Adapter 实现，但不得预先加入 ORM 类型、
数据库 Session 或迁移逻辑。Phase 02B 负责数据库事务、唯一索引、外键和持久化测试，并保持本规格
定义的 HTTP 与 Service 合同不变。

## 13. 已知开发环境风险

本机系统 Python 3.11.5 的 `readline` 原生扩展发生可复现段错误，Pytest 会在捕获初始化时触发。
隔离工作树已改用验证正常的 Python 3.12.0；项目声明仍保持 Python 3.11+，后续 CI 必须覆盖受支持
版本，不能把本机损坏解释器误判为项目兼容性结论。
