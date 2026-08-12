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

## 9. Task 1：FastAPI 依赖、配置与应用骨架（2026-08-12）

### 实际实现 Prompt

```text
实现 Phase 02A 的任务 1：FastAPI 依赖、配置与应用骨架。
先读取任务简报和相关现有代码，只修改 pyproject.toml、backend/app/config.py、
backend/app/main.py、backend/tests/test_config.py、backend/tests/test_project_imports.py。
先写能正常收集且因缺少目标模块失败的配置与健康检查测试；展示红灯原因。
再按简报提供的 Settings 公共合同写最小实现，GET /health 不得调用 AI、不得读取 API Key，
不要实现领域模型、认证、会话或 OpenAI 调用。完成后运行聚焦测试、完整测试、Ruff 和 diff check。
```

### TDD 证据与校正

- 初次执行 `pytest backend/tests/test_config.py -v` 在收集阶段因环境尚未安装 `fastapi` 失败；
  这不是目标行为的 RED。
- 仅先声明并安装简报规定的依赖后重跑，3 项测试按预期 RED：
  `ModuleNotFoundError: backend.app.config`（两项）与
  `ModuleNotFoundError: backend.app.main`（一项）。
- 最小 GREEN 实现只增加不可变 `Settings.from_env()`、`create_app()` 和返回
  `{\"status\": \"ok\"}` 的 `GET /health`，未初始化 OpenAI 客户端或发起网络调用。
- GREEN：聚焦测试与导入测试 `6 passed`；完整套件 `35 passed`；Ruff 输出
  `All checks passed!`；`git diff --check` 无输出。

## 10. Task 2：领域模型、输入不变量与稳定错误（2026-08-12）

### 实际产品与开发 Prompt

```text
实现 Phase 02A 的任务 2：领域模型、输入不变量与稳定错误。
只在 feature/phase-02a-fastapi-memory 的隔离 worktree 修改 backend/app/domain、
backend/tests/test_domain_models.py 和本阶段 Prompt 存档。先阅读任务简报、书面规格、
实施计划、现有 HintLevel 类型和存档格式。

严格 TDD：先写可收集的领域测试并运行，确认 RED 仅由缺失的 backend.app.domain 引起；
随后只实现不可变领域记录、User.create、等级验证及稳定 DomainError 合同。不得提前实现
Repository、Service、认证流程或 API。User.create 必须规范化 email/username_key，拒绝
bool 和非 1..5 整数；默认 UUID 与 now 的行为必须可测，所有领域时间必须为 aware UTC。
完成后记录 RED/GREEN、校正和全套验证证据。
```

### TDD 证据与校正

- RED：执行 `.venv/bin/python -m pytest backend/tests/test_domain_models.py -v`，收集到 9 项；
  全部因 `ModuleNotFoundError: No module named 'backend.app.domain'` 失败，证明目标领域包尚未实现。
- GREEN：新增 frozen 领域记录、`MessageRole`、`User.create()`、UTC 时间检查和稳定错误属性后，
  同一聚焦测试为 `9 passed`。
- 校正：首次 Ruff 检查只报告新增测试的一条超长局部导入和导入排序；将其拆为标准多行导入，
  未更改产品行为。
- 领域边界：`User.create()` 默认以 `uuid4()` 生成 ID、以 `datetime.now(UTC)` 生成时间；注入
  UUID 与 UTC 时间可使测试确定。所有领域记录会拒绝 naive 或非 UTC 时间，防止未来存储层混用
  本地时间。

## 11. Task 3：异步 Repository 与内存原子 Unit of Work（2026-08-12）

### 实际产品与开发 Prompt

```text
实现 Phase 02A 的任务 3：异步 Repository 与内存原子 Unit of Work。
只在 feature/phase-02a-fastapi-memory 的隔离 worktree 修改 backend/app/repositories.py、
backend/app/memory.py、backend/tests/conftest.py、backend/tests/test_memory_repositories.py 和
本阶段 Prompt 存档。先阅读批准规格、实施计划、领域模型/错误及 Prompt 归档格式。

严格 TDD：先写可收集的唯一性、会话所有权、消息排序、Token 摘要查找和过期删除、UOW
commit/rollback、锁复用测试并运行，确认 RED 仅由缺少 backend.app.memory 引起；随后只实现
异步 Repository Protocol、共享 InMemoryStore、每会话 asyncio.Lock 与局部暂存的 Chat UOW。
commit 前不得有任何可见副作用；commit 必须先验证全部 staged 变更，才一起应用学生状态和两条
消息。UUID 始终作为 Repository 资源键；不实现服务、认证、HTTP 或外部网络功能。
完成后运行聚焦与完整 Pytest、Ruff、diff check 和敏感信息扫描，并记录证据。
```

### TDD 证据与校正

- RED：执行 `.venv/bin/python -m pytest backend/tests/test_memory_repositories.py -v`，7 项测试均因
  `ModuleNotFoundError: No module named 'backend.app.memory'` 失败；测试已收集，失败原因仅为目标
  Adapter 不存在。
- GREEN：最小实现提供 `UserRepository`、`TokenRepository`、`SessionRepository`、
  `MessageRepository` 与 `ChatUnitOfWork` Protocol；同一个 `InMemoryStore` 持有全部字典和 Adapter。
  聚焦测试为 `7 passed`，覆盖规范化邮箱/用户名唯一性、会话所有权、按创建时间稳定排序、摘要
  Token 查找/过期删除、未 commit 回滚、commit 双消息与用户状态、同 UUID 的锁复用。
- 原子性校正：UOW 先验证 staged 用户和两条消息的全部冲突，再执行无 `await` 的字典写入；因此
  验证失败不会留下更新后的用户或半条消息。离开 async context 而未 `commit()` 时局部 staged 值
  被丢弃。
- 质量验证：完整套件 `51 passed`（仅现有 FastAPI/Starlette 弃用警告）；Ruff `All checks passed!`；
  `git diff --check` 无输出；新增文件的 `sk-`、私钥和 AWS key 模式扫描无匹配。

### Task 3 审查纠偏（2026-08-12）

```text
修复 Task 3 独立审查发现的 Repository 合同缺口，不进入 Task 4。
先为 Protocol 模块导入、UOW 不完整暂存提交和 frozen/replace 身份字段绕过分别写 RED 回归测试。
最小修复正确的异步 context-manager 类型来源、完整聊天 UOW 提交前置条件，以及 Repository 自己的
邮箱/用户名规范化索引。更新证据后运行目标/完整测试、Ruff、显式导入、diff 与敏感扫描。
```

- 根因：`AsyncContextManager` 被错误地从 `collections.abc` 导入，Python 3.12 导入
  `backend.app.repositories` 时立即抛 `ImportError`；UOW 验证未要求 user 与消息对同时存在；索引键
  直接信任可被 frozen `replace()` 伪造的实体字段。
- RED：新增 5 项回归断言后，目标套件为 `5 failed, 7 passed`：Protocol 导入 `ImportError`、篡改
  身份实体无法按规范化邮箱查询、user-only/messages-only `commit()` 未抛错，以及跨 session 配对
  测试暴露了测试构造错误。后者改为正确的 user/assistant 跨会话对后，仍为所需产品 RED。
- GREEN：改用 `contextlib.AbstractAsyncContextManager`；`commit()` 缺少 staged user 或完整消息对即
  抛 `ValueError` 且没有字典写入；Repository 索引与所有权验证从 `email.strip().lower()` 和
  `username.casefold()` 重新计算，而不是信任 `username_key`。目标测试 `12 passed`，并显式确认
  `import backend.app.repositories` 成功。

## 12. Task 4：密码、随机 Token 与 Auth Service（2026-08-12）

### 实际实现 Prompt

```text
实现 Phase 02A 的任务 4：密码、随机 Token 与 Auth Service。
只在 feature/phase-02a-fastapi-memory 的隔离 worktree 修改 backend/app/security.py、
backend/app/services、backend/tests/conftest.py、backend/tests/test_auth_service.py 和本阶段 Prompt
存档。先阅读批准规格、Task 4 简报、Repository/Memory 合同和已有归档。

严格 TDD：先为密码哈希、只存 Token 摘要、登录凭证错误等价、当前 Token 定向注销、空/未知/过期
Token 拒绝并清理、以及注册唯一性冲突写可收集测试；运行并确认 RED 仅来自尚未实现的服务包。随后
实现 pwdlib recommended 哈希、secrets Token、SHA-256 摘要、hmac constant-time 比较和注入 UTC
clock/TTL/token factory 的 AuthService。明文 Token 只可从 login 返回，不能进入 Repository、日志或
归档；不实现 HTTP Router、环境读取或真实等待。完成后运行聚焦和完整测试、Ruff、diff check 与敏感
模式扫描，并记录真实证据。
```

### TDD 证据与校正

- RED：在新增 `test_auth_service.py` 和确定性 `store`/`auth_service` fixtures 后，执行
  `.venv/bin/python -m pytest backend/tests/test_auth_service.py -v`；收集初始化仅因
  `ModuleNotFoundError: No module named 'backend.app.services'` 失败，表明目标 Service 尚未实现。
- GREEN：最小实现新增 `PasswordHash.recommended()` 包装、`secrets.token_urlsafe(32)`、SHA-256
  Token 摘要和 `hmac.compare_digest`；AuthService 只写摘要，登录调用者获得 `IssuedToken` 中的明文。
  可注入 UTC clock、TTL 和 token factory，故测试不读取环境也不 sleep。
- 安全校正：未知邮箱和错误密码统一为完全相同的 `AuthenticationError` code/message；空、未知、过期、
  被撤销及失去用户的 Token 统一为稳定的无效 Token 错误。过期 Token 在拒绝前删除，退出会先认证并只
  删除当前摘要，保留同一用户的其他 Token。
- 重构：GREEN 后 Ruff 指出安全模块的标准库导入排序和测试超长行；只整理导入及换行，未改变行为。

### Task 4 正式审查纠偏（2026-08-12，复审待定）

```text
修复 Task 4 正式审查发现的登录失败路径时序枚举风险，不进入 Task 5。
先写不依赖耗时阈值的 RED：以 monkeypatch 记录 password verify 调用，证明未知邮箱与错误密码都必须
执行一次校验。实现一个只初始化一次的 dummy password hash；未知邮箱使用它、已知用户使用该用户 hash，
两条路径再统一抛相同 AuthenticationError。同步纠正审计报告中在正式审查前预写的 PASS，不得写入任何
复审成功结论。完成后记录 RED/GREEN，并运行聚焦与全量验证。
```

- 正式审查 FAIL 发现 1：登录条件使用 `user is None or not verify_password(...)`；Python 的短路使未知
  邮箱不执行 Argon2，而错误密码会执行，产生可被大量采样利用的时序差异。
- RED：新增 monkeypatch 调用记录测试，先对不存在邮箱、再对错误密码登录；修复前记录仅有一次校验，
  断言 `len(verified_hashes) == 2` 以 `1 != 2` 失败。测试不测真实耗时，也不输出密码或 Token。
- 正式审查 FAIL 发现 2：Task 4 报告在正式审查发生前错误地写入 `Independent Review PASS`；该段已删除，
  报告现明确记录首次正式审查 FAIL 与复审待定。
- GREEN：`DUMMY_PASSWORD_HASH` 在模块加载时仅构造一次；登录先选择用户 hash 或 dummy hash，再无条件
  调用一次 `verify_password()`，最后统一判断 user/password validity。新增 RED 回归测试变为通过；正式
  复审结论仍待独立审查，不在此处预写通过。

## 13. Task 5：认证、当前用户 API 与统一错误响应（2026-08-12）

### 实际实现 Prompt

```text
实现 Phase 02A 的任务 5：认证、当前用户 API 与统一错误响应。
先读取 Task 5 简报、批准规格、实施计划、现有 AuthService、main/config/domain/errors，以及本 Prompt
存档的格式。严格 TDD：先写 FastAPI TestClient 注册、登录、当前用户、退出、Token 失败等价、冲突、
严格等级验证、OpenAPI 和两个默认 app 实例隔离测试，运行并确认 RED 是缺失 client/router；再以最小
Pydantic Schema、Bearer dependency、auth/users Router、DomainError handler 和 app.state.container 让它们
转绿。请求等级必须拒绝 bool/float；成功响应不得包含密码 hash、effective level、内部 hints 或 Token
digest。422 必须保留可定位的安全验证信息且不得回显密码。默认装配不得调用 AI、访问网络或要求 Key，
且 /health 必须保持独立。不要实现 Task 6 会话。
```

### TDD 证据与校正

- RED：新增 `test_auth_api.py` 后运行
  `.venv/bin/python -m pytest backend/tests/test_auth_api.py -v`，4 项均因 `client` fixture 尚不存在报错；
  这证明 API 测试可收集且 HTTP 容器尚未实现。
- GREEN：每次 `create_app()` 建立独立的 `InMemoryStore`/`AuthService` 默认容器，测试 fixture 也注入独立
  固定时钟服务；`app.state.container` 只属于该 app 实例，无模块级内存字典。
- 校正：FastAPI 默认的 422 载荷会包含失败字段的 `input`，这可能回显密码。新增
  `RequestValidationError` handler 后返回稳定 `validation_error` 和 Pydantic 的 `loc/msg/type`，保留可用
  字段定位但不返回原始输入或内部栈信息。临时移除 handler 后，新增测试按预期 RED（`KeyError: 'error'`），
  恢复最小 handler 后转绿。
- Bearer 校正：缺失、`Basic` 畸形和未知 Bearer 凭证都进入同一 AuthService `invalid_token` 路径，响应为
  `401`、同一安全错误代码，并带 `WWW-Authenticate: Bearer`。退出复用成功鉴权后的原始 Bearer 值，只撤销
  当前 Token，返回无 body 的 `204`。

## 14. Task 6：会话创建、列表、历史和所有权 API（2026-08-12）

### 实际实现 Prompt

```text
实现 Phase 02A Task6。工作树 feature/phase-02a-fastapi-memory。严格 TDD，实现 ChatService 的
create/list sessions/list messages 三个精确 async 公共方法和 sessions router/schemas/container wiring。
所有权必须在查询边界 enforced；不存在与他人资源完全同 404 code/message，防枚举。标题 None/去空白/
空白结果的合同按 spec/plan推导并测试，最大120，严格请求字段；UUID path 无效时安全422。会话列表排序按
批准规格；消息公共响应只暴露计划允许字段，稳定排序；空历史。认证复用 Task5。无 Task7+ analyzer/
provider/post-message。追加 Prompt/TDD 证据，运行 focused/full/Ruff/diff/sensitive，提交并推送。
```

### TDD 证据与校正

- RED：新增 `test_sessions_api.py` 后运行
  `.venv/bin/python -m pytest backend/tests/test_sessions_api.py -v`，收集到 5 项并全部按预期失败：
  未注册 Router 的 `POST /sessions` 和 UUID 路径均为 404，且 `backend.app.services.chat` 不存在。
- GREEN：`ChatService` 只公开三个异步方法：创建、按用户列出会话、以及在 `get_for_user()` 查询边界
  校验所有权后读取消息。未知会话和非所有者都构造相同的
  `NotFoundError("session_not_found", "Session not found")`，不泄露资源存在性。
- 标题校正：Schema 允许省略或显式 `null`，拒绝额外字段；Service 对非空标题先 `strip()`，空白结果
  存为 `None`，并在去空白后执行 120 字符上限。响应消息仅序列化 `id`、`session_id`、`role`、`content`
  和 `created_at`，不公开评估、提示等级、Provider、模型或 Token 用量。
- GREEN/回归：聚焦 sessions + auth API 为 `10 passed`；全套离线测试为 `76 passed`；任务 Ruff 输出
  `All checks passed!`；`git diff --check` 无输出。测试覆盖双用户隔离、未知/非 owner 完全相同 404、
  会话与消息稳定创建时间排序、空历史、标题边界、无效 UUID 的安全 422，以及两个默认 app 实例的内存隔离。
