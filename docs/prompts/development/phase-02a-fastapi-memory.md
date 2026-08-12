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

### Task 6 审查纠偏：时间并列排序（2026-08-12，复审待定）

```text
Task6 审查 FAIL：memory.py 的 session/message list 只按 created_at 排序，时间并列时会依赖字典插入顺序。
先用固定相同 timestamp、反向插入和可预测 UUID 添加 RED 回归，覆盖 Repository 的 session/message list
及 API 的 session list；保持批准的 created_at 升序主排序。随后仅用 UUID 整数作为升序次键，运行聚焦、
全量、Ruff、diff 和敏感扫描。记录真实首次审查 FAIL，不能预写复审 PASS。
```

- 首次审查 FAIL：`InMemorySessionRepository.list_for_user()` 与
  `InMemoryMessageRepository.list_for_session()` 的 key 都只有 `created_at`。Python 稳定排序会保留字典插入
  顺序，故同一时间戳的返回顺序可由写入顺序改变，未满足稳定的 API/Repository 合同。
- RED：固定相同 UTC timestamp，以较大 UUID 先插入、较小 UUID 后插入；Repository 的 session/message
  断言以及 session API 断言均失败，实际先返回较大 UUID，证明失败来自缺失的显式次键。
- GREEN：两个 Repository 均改为 `(created_at, id.int)` 升序，保持既有创建时间升序方向；UOW 既有测试
  的随机 UUID 与同 timestamp 的插入顺序假设不再成立，改为显式递增 UUID，使其继续只测试原子提交。
- 本次纠偏的复审结论待独立审查，不在此处预写通过。

## 15. Task 7：Problem Analyzer 合同与确定性 Mock（2026-08-12）

### 实际实现 Prompt

```text
实现 Phase02A Task7。工作树 feature/phase-02a-fastapi-memory，禁止 main。完整读取 Task7
简报、批准规格/计划、现有 ai/domain/pedagogy/Prompt；严格 TDD。创建 frozen AnalyzerRequest、
async ProblemAnalyzer Protocol 和确定性 Mock。难度规则仅使用固定关键词，编程与数学独立且严格为
1..5。规范化必须稳定地处理大小写、Unicode 全半角及首尾/内部空白；ASCII 关键词按词边界，中文
关键词按字串。recent_messages 的批准澄清为仅含用户消息、按旧到新排列，最后一项是最近问题；只有
非空的规范化文本与该项相等时 same_problem 为真。规格没有 elaboration 判定规则，因此 mock 始终返回
False，不能声称语义智能。无网络、Key、随机性，不实现 Task8 provider。追加 Prompt/TDD/边界说明，
运行聚焦、完整、Ruff、diff 和敏感扫描，提交并推送。
```

### TDD 证据与边界说明

- RED：先新增 `test_analyzer.py`，运行 `.venv/bin/python -m pytest backend/tests/test_analyzer.py -v`；6 项
  均因 `ModuleNotFoundError: backend.app.ai.analyzer` 失败，失败原因仅是目标模块尚未实现。
- 规则：编程关键词为 `bug/code/coding/error/exception/for/function/loop/program/programming/python/syntax/variable/while`
  和 `代码/函数/循环/报错/异常/语法/程序/编程/变量/错误`；数学关键词为
  `algebra/calculus/derivative/equation/integral/math/maths/mathematics/matrix/vector` 和
  `代数/导数/微积分/方程/积分/向量/数学/矩阵`。命中返回该维度 3，不命中返回 1；两个维度独立。
- 历史语义澄清：`AnalyzerRequest.recent_messages` 不是完整带角色 transcript；它只能传入用户问题，按
  时间从旧到新排列。Mock 只比较最后一个条目。NFKC、`casefold()` 与空白折叠后，两个非空文本完全相等才是
  `same_problem=True`；空文本永远不是同一题。标点不被删除，因此相同标点文本可精确相等。
- `is_elaboration` 的批准规格、计划和 Task7 简报均未提供固定判定。为避免无依据的语义推断，这个纯测试
  替身固定返回 `False`；后续真实 Analyzer 仍须经过既有 metadata 校验与跨字段不变量处理。

## 16. Task 8：异步 Tutor Provider 迁移与一次重试策略（2026-08-12）

### 实际实现 Prompt

```text
实现 Phase02A Task8。工作树 feature/phase-02a-fastapi-memory，禁止 main。完整读取 Task8
简报、批准规格/计划、Phase01 provider/mock/cli/tests/types/prompt archive。严格 TDD：先迁移/新增测试
产生有效 RED。TutorProvider async，Mock async deterministic，generic retry_once 恰好最多2 attempts；
只 retry transient，non-transient不sleep，第二次异常原样传播；sleep注入，默认不得真实sleep的测试。
考虑 CancelledError/BaseException 不应吞；类型注解泛型。CLI用 asyncio.run，Phase01 stdout JSON合同逐字段
不变，错误/exit行为不意外变。查找所有 generate 调用同步点并迁移，不能留下 coroutine 泄漏。无 Task9
chat orchestration、无 OpenAI。追加 Prompt/TDD/迁移决策。apply_patch。focused/full/Ruff/diff/sensitive，
实际运行 CLI比对关键JSON（programming3 maths1 provider/model）。提交并推送。
```

### TDD 证据与迁移决策

- RED：先把两个 Mock Provider 测试改为 `pytest.mark.asyncio` 并 `await generate()`，新增四个一次重试
  测试。执行 `.venv/bin/python -m pytest backend/tests/test_mock_provider.py backend/tests/test_retry.py -v` 收集到
  6 项；两个 Provider 测试按预期以 `TypeError: object TutorResponse can't be used in 'await' expression` 失败，
  四个重试测试仅因 `backend.app.ai.retry` 不存在失败。
- GREEN：`TutorProvider.generate()` 和 `MockTutorProvider.generate()` 都改为异步；Mock 内容、名称与 Token
  估算未变，仍离线且确定。仓库内所有 `generate()` 调用点均已检查，CLI 是唯一同步调用点，现由异步
  `_run(args)` await，`main()` 用 `asyncio.run()` 保持参数解析、JSON stdout 和 argparse 退出行为。
- 重试边界：`retry_once` 用 `TypeVar` 保留任意异步操作返回类型。只捕获 `Exception`，因此
  `asyncio.CancelledError` 等 `BaseException` 不会被吞掉；首个 transient 异常仅 sleep 一次后再调用一次，
  第二次的异常不包裹、不转换。非 transient 异常直接原样抛出且不 sleep。测试将 sleep 注入为 async no-op，
  所以测试没有真实等待；生产默认仍使用 `asyncio.sleep(0.25)`。
- 聚焦 GREEN：Provider、Retry 和 CLI 测试为 `8 passed`；Ruff 对相关产品和测试文件输出
  `All checks passed!`。完整套件、实际 CLI JSON、diff 和敏感信息扫描在提交前重新运行并记录在 Task 8
  报告中。

## 17. Task 9：原子 Chat Service 教学回合（2026-08-12）

### 实际实现 Prompt

```text
实现 Phase02A Task9。工作树 feature/phase-02a-fastapi-memory，禁止 main。完整读 task9 brief、批准
spec/plan、所有 ai/domain/memory/chat代码和Phase01教学/Prompt tests/Prompt归档。严格TDD。

send_message锁内顺序必须：owner check → history 最近10条且总content最多4000字符（明确从最新向后预算后
恢复时间顺序，不截断敏感语义除非spec定义）→ Analyzer → coerce metadata → hint levels → 两个EMA update →
build prompt → Tutor → stage完整 user+assistant+updated user → commit。AnalyzerRequest recent_messages 只能用户
历史且 oldest→newest；当前消息不重复塞历史。Prompt context字段映射精确，不能泄露隐藏levels给公开返回但
内部消息metadata要完整审计。创建时间/UUID注入以可测并确保两个消息顺序；roles/assessment/hints/provider/
model/token counts正确归属。失败 analyzer/tutor/metadata/prompt/UOW 都应零部分写；同session并发串行且第二
回合看到第一回合历史/状态；不同session不要共享同锁。first-turn hint cap/EMA遵守Phase01合同。

对 provider/analyzer transient retry 是否属于 Task9 请严格按spec，不擅自扩展。content输入服务层不变量
（空/长度）查spec。避免 holding lock 之外TOCTOU。测试成功、各失败、rollback、并发、history budget/order、
ownership、state evolution。
```

### TDD 证据与边界说明

- RED：新增 `test_chat_service.py` 后运行
  `.venv/bin/python -m pytest backend/tests/test_chat_service.py -v`，收集到 11 项，均因
  `ChatService.__init__()` 尚不接受 Task 9 的 User Repository、Analyzer、Tutor、UOW 和会话锁依赖而失败；
  这证明服务尚不能编排教学回合。随后以固定时钟和反向 UUID 新增跨两回合的消息排序回归，修复前单独运行按
  预期失败：`second` 在 `first` 之前，证明同一固定时钟下需要显式维护创建顺序。
- GREEN：`send_message()` 在同一 session 的 `asyncio.Lock` 内执行所有权校验、连续的最新历史后缀、Analyzer、
  严格 Assessment 类型/范围校验、Phase 01 metadata coercion、双 hint/EMA、Prompt、Tutor 和单个 UOW commit。
  只把用户历史（旧到新）交给 `AnalyzerRequest`；Prompt 的 `recent_messages` 为完整带角色历史序列。历史从最新
  向后逐条预算，达到 10 条或 4,000 个 content 字符即停止，随后恢复时间顺序；不会截断任意已选消息。
- 原子性：两条 `ChatMessage` 与 `replace()` 得到的完整 User 新状态均仅在 Tutor 成功后 stage，随后一次 commit。
  Analyzer、Schema/metadata、Prompt、Tutor 或 UOW 失败时，测试均证明没有新消息也没有状态修改。用户消息保存
  Assessment 与两个 hint 作为内部审计；助手消息保存 Provider、模型和输入/输出 Token。Task 10 的公开 Schema
  仍负责筛除这些内部字段。
- 时间与并发：时钟和 UUID factory 都可注入；助手时间必晚于用户时间，并在固定时钟时以前一条历史消息为下界，
  防止 Repository 的 `(created_at, UUID)` 稳定排序打散多个回合。外部模型调用也保持该 session 锁，因此第二个
  同会话请求在第一回合提交后才读取历史与用户状态；`InMemoryStore` 继续按 UUID 各自维护不同 session 的锁。
- 重试边界：没有在本任务把 `retry_once` 包进 Analyzer 或 Tutor。Task 9 批准数据流未列出重试；Task 8 仅提供
  通用策略，真实上游适配器将在后续 Task 11 按瞬时错误分类接入，避免重复重试或在 Mock 路径引入等待。

### Task 9 严格审查纠偏（2026-08-12，复审待定）

```text
Task9 严格审查 FAIL：修复同一 User 跨 session 的 EMA 丢失、未校验的 TutorResponse，以及按正文而不是
Prompt 序列化长度预算历史。每项先写确定性 RED；采用 user lock → session lock 的固定顺序，禁止全局锁；
Tutor 结果在 stage 前严格校验；历史必须按最终转义后的序列化长度保留最新连续后缀，不能交给 Prompt Builder
从开头截断。完成后记录首次 FAIL 与复审待定，不预写 PASS。
```

- 首次严格审查 FAIL（Critical）：原实现只持有 session 锁。两个属于同一 User 的不同 session 可同时读取同一
  effective level，分别计算 EMA 后后写者覆盖前者，丢失一次学习状态更新。RED 使用首个 Tutor barrier 固定该
  交错：修复前第二个 session 已进入 Tutor，最终只保留一次更新。
- 修复：`InMemoryStore` 新增按 User UUID 复用的 `asyncio.Lock`。完整回合统一先获取 user lock、再获取
  session lock；因此不存在反向锁顺序。该用户的 Analyzer、状态读取、EMA、Tutor 和 UOW 均串行，而不同 User
  持有不同锁仍可在首个 Tutor 被阻塞时完成自己的 session。GREEN 验证两次同难度更新得到串行两次 EMA 的
  `2.144`，并验证不同用户不互相阻塞。
- 首次严格审查 FAIL（Important）：`TutorResponse` 只靠类型注解，任意对象、空字符串、bool Token 或负 Token
  都可能被保存，或者在属性访问时抛非稳定异常。新增参数化 RED 覆盖对象、空 content/provider/model、bool、
  非整数和负数。服务现在要求非空字符串及非 bool 的非负整数 Token；所有无效响应在 stage 前统一抛出
  `UpstreamInvalidResponseError("invalid_tutor_response", "Tutor returned an invalid response")`，并证明零写入。
- 首次严格审查 FAIL（Important）：历史只累加正文长度；`user: `、`assistant: `、换行和 HTML 转义会让实际
  Prompt 字段超过 4,000，随后 Prompt Builder 从开头截断，丢掉最新内容。`RecentHistory` 现从最新向后按
  Prompt Builder 同样的 HTML 转义长度预算并恢复时间顺序。单条超限消息保留带明确 `[truncated]` 标志的最新尾部；
  Analyzer 仍接收同一已选历史消息的完整用户文本。4,000 正文、角色前缀/换行精确边界、多条连续后缀和 HTML
  转义回归均证明 Prompt Builder 不再进行额外截断，最新 sentinel 保留。
- 复审结论：待独立审查；本记录只保留首次 FAIL、RED/GREEN 和当前验证证据，不宣称复审通过。
