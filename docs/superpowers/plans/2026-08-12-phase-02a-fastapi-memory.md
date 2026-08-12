# Phase 02A FastAPI 内存后端实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在保留 Phase 01 确定性教学核心的前提下，构建带内存用户、随机 Bearer Token、受保护会话、Mock/Real Analyzer 与 Tutor Provider 的 FastAPI 后端。

**架构：** FastAPI Router 只处理协议和错误映射，Auth/Chat Service 负责编排，异步 Repository Protocol 隔离内存存储，Phase 01 Pedagogy Engine 保持纯函数。默认测试路径使用 Mock Analyzer 与 Mock Tutor；OpenAI Responses API 只在显式配置和人工冒烟测试中启用。

**技术栈：** Python 3.11+、FastAPI、Pydantic v2、HTTPX/TestClient、pwdlib/Argon2、OpenAI Python SDK、Pytest、Ruff。

---

## 文件结构

### 创建

- `backend/app/config.py`：环境变量解析与应用配置。
- `backend/app/domain/models.py`：User、AuthToken、ChatSession、ChatMessage、ProblemAssessment。
- `backend/app/domain/errors.py`：稳定领域错误码与异常类型。
- `backend/app/repositories.py`：异步 Repository Protocol 和 Unit of Work 合同。
- `backend/app/memory.py`：线程内内存 Repository、每会话锁和原子提交实现。
- `backend/app/security.py`：密码哈希、随机 Token、Token 摘要和常量时间比较。
- `backend/app/services/auth.py`：注册、登录、退出和当前用户服务。
- `backend/app/services/chat.py`：会话与原子聊天回合编排。
- `backend/app/ai/analyzer.py`：Problem Analyzer Protocol 与请求类型。
- `backend/app/ai/mock_analyzer.py`：确定性离线分析器。
- `backend/app/ai/retry.py`：一次瞬时错误重试策略。
- `backend/app/ai/openai_adapters.py`：OpenAI Analyzer 与 Tutor Adapter。
- `backend/app/api/schemas.py`：Pydantic 请求/响应模型。
- `backend/app/api/dependencies.py`：配置、Service 和 Bearer 用户依赖。
- `backend/app/api/auth.py`：注册、登录和退出 Router。
- `backend/app/api/users.py`：当前用户 Router。
- `backend/app/api/sessions.py`：会话和聊天 Router。
- `backend/app/api/errors.py`：统一错误响应与异常处理器。
- `backend/app/main.py`：FastAPI 应用工厂与默认装配。
- `backend/tests/test_config.py`
- `backend/tests/test_domain_models.py`
- `backend/tests/test_memory_repositories.py`
- `backend/tests/test_auth_service.py`
- `backend/tests/test_auth_api.py`
- `backend/tests/test_sessions_api.py`
- `backend/tests/test_analyzer.py`
- `backend/tests/test_retry.py`
- `backend/tests/test_chat_service.py`
- `backend/tests/test_chat_api.py`
- `backend/tests/test_openai_adapters.py`
- `backend/tests/test_openai_live.py`
- `backend/tests/conftest.py`：跨任务复用的时钟、工厂、内存容器和 TestClient fixtures。
- `.env.example`：只保存变量名和安全示例值。
- `docs/08-fastapi-memory-backend.md`：运行、接口、边界与人工体验说明。

### 修改

- `pyproject.toml`：运行依赖、开发依赖和 live test marker。
- `.gitignore`：明确忽略 `.env`，但继续跟踪 `.env.example`。
- `backend/app/ai/provider.py`：Tutor Provider 改为异步合同。
- `backend/app/ai/mock_provider.py`：异步 Mock 实现。
- `backend/app/cli.py`：用 `asyncio.run()` 保持 CLI 可运行。
- `backend/tests/test_mock_provider.py`：异步 Provider 合同测试。
- `backend/tests/test_cli.py`：保持既有 CLI 行为回归。
- `README.md`：Phase 02A 运行入口与阶段进度。
- `docs/prompts/development/phase-02a-fastapi-memory.md`：逐任务 Prompt、红灯、校正和验收记录。

## 全局执行约束

- 所有任务都在 `feature/phase-02a-fastapi-memory` worktree 完成，不修改 `main`。
- 每个任务先运行指定测试得到与缺失行为一致的红灯，再写最小实现。
- 每次提交前运行目标测试、相关回归测试、`ruff check` 和 `git diff --check`。
- 每次提交后推送当前分支；Prompt 和典型错误追加到阶段存档。
- 默认测试不得访问网络、读取真实 API Key 或等待真实退避时间。
- 直到任务 11 才创建/配置 OpenAI API Key；Key 不得粘贴到聊天、代码、测试或 Git。

### 任务 1：FastAPI 依赖、配置与应用骨架

**文件：**
- 修改：`pyproject.toml`
- 创建：`backend/app/config.py`
- 创建：`backend/app/main.py`
- 创建：`backend/tests/test_config.py`
- 修改：`backend/tests/test_project_imports.py`

- [ ] **步骤 1：编写失败的配置和健康检查测试**

```python
from fastapi.testclient import TestClient


def test_settings_default_to_mock_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("APP_PROVIDER_MODE", raising=False)

    from backend.app.config import Settings

    settings = Settings.from_env()
    assert settings.provider_mode == "mock"
    assert settings.analyzer_model == "gpt-5.6-luna"
    assert settings.tutor_model == "gpt-5.6-terra"
    assert settings.token_ttl_seconds == 86_400


def test_openai_mode_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_PROVIDER_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from backend.app.config import Settings

    try:
        Settings.from_env()
    except ValueError as exc:
        assert str(exc) == "OPENAI_API_KEY is required in openai mode"
    else:
        raise AssertionError("expected configuration error")


def test_health_endpoint_does_not_call_ai() -> None:
    from backend.app.main import create_app

    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **步骤 2：运行测试并确认红灯来自缺少模块**

运行：`.venv/bin/python -m pytest backend/tests/test_config.py -v`  
预期：FAIL，`ModuleNotFoundError: backend.app.config` 或 `backend.app.main`。

- [ ] **步骤 3：添加依赖和最小应用骨架**

在 `pyproject.toml` 中设置：

```toml
dependencies = [
  "fastapi>=0.116,<1.0",
  "httpx>=0.28,<1.0",
  "openai>=2.0,<3.0",
  "pwdlib[argon2]>=0.2,<1.0",
  "pydantic[email]>=2.11,<3.0",
  "uvicorn[standard]>=0.35,<1.0",
]
```

开发依赖增加 `pytest-asyncio>=1.1,<2.0`，并在 pytest 配置中设置 `asyncio_mode = "auto"`。若
安装时发现当前官方 OpenAI SDK 已超过该主版本范围，先查阅官方 Python SDK 发布信息并更新规格，
不能静默改用旧 Chat Completions API。

`backend/app/config.py` 的公开合同：

```python
@dataclass(frozen=True)
class Settings:
    provider_mode: Literal["mock", "openai"] = "mock"
    openai_api_key: str | None = None
    analyzer_model: str = "gpt-5.6-luna"
    tutor_model: str = "gpt-5.6-terra"
    reasoning_effort: str = "medium"
    openai_timeout_seconds: float = 30.0
    token_ttl_seconds: int = 86_400

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("APP_PROVIDER_MODE", "mock").strip().lower()
        if mode not in {"mock", "openai"}:
            raise ValueError("APP_PROVIDER_MODE must be mock or openai")
        api_key = os.getenv("OPENAI_API_KEY") or None
        if mode == "openai" and api_key is None:
            raise ValueError("OPENAI_API_KEY is required in openai mode")
        return cls(
            provider_mode=cast(Literal["mock", "openai"], mode),
            openai_api_key=api_key,
            analyzer_model=os.getenv("OPENAI_ANALYZER_MODEL", "gpt-5.6-luna"),
            tutor_model=os.getenv("OPENAI_TUTOR_MODEL", "gpt-5.6-terra"),
            reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "medium"),
            openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
            token_ttl_seconds=int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400")),
        )
```

`backend/app/main.py` 提供 `create_app() -> FastAPI` 和不依赖 AI 的 `GET /health`。

- [ ] **步骤 4：安装依赖并验证通过**

运行：

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest backend/tests/test_config.py backend/tests/test_project_imports.py -v
.venv/bin/python -m ruff check backend/app/config.py backend/app/main.py backend/tests/test_config.py
```

预期：全部 PASS；Ruff 输出 `All checks passed!`。

- [ ] **步骤 5：存档并提交**

```bash
git add pyproject.toml backend/app/config.py backend/app/main.py backend/tests/test_config.py backend/tests/test_project_imports.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "chore: bootstrap phase 02a FastAPI app (task 1/12)"
git push
```

### 任务 2：领域模型、输入不变量与稳定错误

**文件：**
- 创建：`backend/app/domain/__init__.py`
- 创建：`backend/app/domain/models.py`
- 创建：`backend/app/domain/errors.py`
- 创建：`backend/tests/test_domain_models.py`

- [ ] **步骤 1：编写失败的领域模型测试**

```python
from datetime import UTC, datetime

import pytest


def test_user_normalizes_identity_and_initializes_effective_levels() -> None:
    from backend.app.domain.models import User

    user = User.create(
        email=" Student@Example.COM ",
        username="Student_1",
        password_hash="argon2-hash",
        self_programming_level=2,
        self_maths_level=4,
        now=datetime(2026, 8, 12, tzinfo=UTC),
    )
    assert user.email == "student@example.com"
    assert user.username_key == "student_1"
    assert user.effective_programming_level == 2.0
    assert user.effective_maths_level == 4.0


@pytest.mark.parametrize("value", [0, 6, True, 2.5])
def test_self_levels_reject_invalid_values(value) -> None:
    from backend.app.domain.models import User

    with pytest.raises(ValueError, match="level must be an integer from 1 to 5"):
        User.create(
            email="student@example.com",
            username="student",
            password_hash="hash",
            self_programming_level=value,
            self_maths_level=3,
        )
```

- [ ] **步骤 2：运行并确认缺少领域类型的红灯**

运行：`.venv/bin/python -m pytest backend/tests/test_domain_models.py -v`  
预期：FAIL，`ModuleNotFoundError: backend.app.domain`。

- [ ] **步骤 3：实现不可变领域类型与错误合同**

`models.py` 必须定义：

```python
class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ProblemAssessment:
    programming_difficulty: int
    maths_difficulty: int
    same_problem: bool
    is_elaboration: bool


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    username: str
    username_key: str
    password_hash: str
    self_programming_level: int
    self_maths_level: int
    effective_programming_level: float
    effective_maths_level: float
    programming_hint_level: HintLevel
    maths_hint_level: HintLevel
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AuthToken:
    token_digest: str
    user_id: UUID
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class ChatSession:
    id: UUID
    user_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ChatMessage:
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    assessment: ProblemAssessment | None = None
    programming_hint_level: HintLevel | None = None
    maths_hint_level: HintLevel | None = None
    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
```

`errors.py` 必须提供 `DomainError(code, safe_message)` 以及 `AuthenticationError`、
`ConflictError`、`NotFoundError`、`UpstreamInvalidResponseError`、`UpstreamUnavailableError`。

- [ ] **步骤 4：运行领域与 Phase 01 回归测试**

```bash
.venv/bin/python -m pytest backend/tests/test_domain_models.py backend/tests/test_pedagogy.py -v
.venv/bin/python -m ruff check backend/app/domain backend/tests/test_domain_models.py
```

预期：全部 PASS。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/domain backend/tests/test_domain_models.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: define phase 02a domain models (task 2/12)"
git push
```

### 任务 3：异步 Repository 与内存原子 Unit of Work

**文件：**
- 创建：`backend/app/repositories.py`
- 创建：`backend/app/memory.py`
- 创建：`backend/tests/conftest.py`
- 创建：`backend/tests/test_memory_repositories.py`

- [ ] **步骤 1：编写失败的唯一性、所有权和回滚测试**

```python
import pytest


@pytest.mark.asyncio
async def test_user_repository_enforces_normalized_uniqueness(user_factory) -> None:
    from backend.app.domain.errors import ConflictError
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    await store.users.add(user_factory(email="Student@Example.com", username="Student"))
    with pytest.raises(ConflictError):
        await store.users.add(user_factory(email="student@example.com", username="Other"))


@pytest.mark.asyncio
async def test_chat_uow_discards_messages_and_state_without_commit(user_factory) -> None:
    from backend.app.memory import InMemoryStore

    store = InMemoryStore()
    user = user_factory()
    await store.users.add(user)
    changed = replace(user, effective_programming_level=4.0, effective_maths_level=4.0)
    async with store.chat_uow() as uow:
        uow.stage_user(changed)
    assert (await store.users.get(user.id)).effective_programming_level == user.effective_programming_level
    assert await store.messages.list_for_session("missing") == []
```

- [ ] **步骤 2：运行并确认 Repository 尚不存在**

运行：`.venv/bin/python -m pytest backend/tests/test_memory_repositories.py -v`  
预期：FAIL，缺少 `backend.app.memory`。

- [ ] **步骤 3：实现异步 Protocol 和内存 Adapter**

`repositories.py` 定义异步 `UserRepository`、`TokenRepository`、`SessionRepository`、
`MessageRepository` 和 `ChatUnitOfWork` Protocol。`memory.py` 使用单一 `InMemoryStore` 持有字典，
每个会话使用 `asyncio.Lock`；Unit of Work 在 `commit()` 前只保存局部暂存值。

`backend/tests/conftest.py` 此时建立固定 UTC 时钟和 `user_factory`：

```python
@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


@pytest.fixture
def user_factory(fixed_now):
    def build(**overrides) -> User:
        values = {
            "email": "student@example.com",
            "username": "student",
            "password_hash": "argon2-hash",
            "self_programming_level": 2,
            "self_maths_level": 3,
            "now": fixed_now,
        }
        values.update(overrides)
        return User.create(**values)
    return build
```

核心方法签名：

```python
class ChatUnitOfWork(Protocol):
    def stage_messages(self, user_message: ChatMessage, assistant_message: ChatMessage) -> None: ...
    def stage_user(self, user: User) -> None: ...
    async def commit(self) -> None: ...


class InMemoryStore:
    def session_lock(self, session_id: UUID) -> asyncio.Lock: ...
    def chat_uow(self) -> InMemoryChatUnitOfWork: ...
```

- [ ] **步骤 4：验证 Repository 行为**

```bash
.venv/bin/python -m pytest backend/tests/test_memory_repositories.py -v
.venv/bin/python -m ruff check backend/app/repositories.py backend/app/memory.py backend/tests/test_memory_repositories.py
```

预期：唯一性、排序、所有权和 commit/rollback 测试全部 PASS。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/repositories.py backend/app/memory.py backend/tests/conftest.py backend/tests/test_memory_repositories.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: add in-memory repository boundary (task 3/12)"
git push
```

### 任务 4：密码、随机 Token 与 Auth Service

**文件：**
- 创建：`backend/app/security.py`
- 创建：`backend/app/services/__init__.py`
- 创建：`backend/app/services/auth.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_auth_service.py`

- [ ] **步骤 1：编写失败的认证服务测试**

```python
import pytest


@pytest.mark.asyncio
async def test_register_hashes_password_and_login_returns_one_time_token(auth_service, store) -> None:
    user = await auth_service.register(
        email="student@example.com",
        username="student",
        password="correct horse battery",
        self_programming_level=2,
        self_maths_level=3,
    )
    stored = await store.users.get(user.id)
    assert "correct horse battery" not in stored.password_hash

    issued = await auth_service.login(email="student@example.com", password="correct horse battery")
    assert issued.token
    stored_token = await store.tokens.get_by_digest(digest_token(issued.token))
    assert stored_token is not None
    assert stored_token.token_digest != issued.token
    assert await auth_service.authenticate(issued.token) == user


@pytest.mark.asyncio
async def test_logout_revokes_only_current_token(auth_service) -> None:
    await auth_service.register(
        email="student@example.com", username="student", password="correct horse battery",
        self_programming_level=2, self_maths_level=3,
    )
    first = await auth_service.login(email="student@example.com", password="correct horse battery")
    second = await auth_service.login(email="student@example.com", password="correct horse battery")
    await auth_service.logout(first.token)
    with pytest.raises(Exception):
        await auth_service.authenticate(first.token)
    assert await auth_service.authenticate(second.token)
```

- [ ] **步骤 2：运行并确认 Auth Service 缺失**

运行：`.venv/bin/python -m pytest backend/tests/test_auth_service.py -v`  
预期：FAIL，缺少 `backend.app.services.auth`。

- [ ] **步骤 3：实现安全函数与 Auth Service**

`security.py` 的公开合同：

```python
PASSWORD_HASHER = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return PASSWORD_HASHER.verify(password, password_hash)


def create_bearer_token() -> str:
    return secrets.token_urlsafe(32)


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_digest_matches(token: str, digest: str) -> bool:
    return hmac.compare_digest(digest_token(token), digest)
```

`AuthService` 注入时钟和 Token TTL，测试不得依赖真实时间或睡眠。登录失败统一抛
`AuthenticationError("invalid_credentials", "Invalid email or password")`，不能泄露邮箱是否存在。
在 `conftest.py` 增加 `store` 和 `auth_service` fixtures；`auth_service` 使用固定时钟、内存 Store 和
86,400 秒 TTL，不能读取进程环境。

- [ ] **步骤 4：验证认证核心**

```bash
.venv/bin/python -m pytest backend/tests/test_auth_service.py backend/tests/test_memory_repositories.py -v
.venv/bin/python -m ruff check backend/app/security.py backend/app/services/auth.py backend/tests/test_auth_service.py
```

预期：全部 PASS。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/security.py backend/app/services backend/tests/conftest.py backend/tests/test_auth_service.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: implement in-memory authentication core (task 4/12)"
git push
```

### 任务 5：认证、当前用户 API 与统一错误响应

**文件：**
- 创建：`backend/app/api/__init__.py`
- 创建：`backend/app/api/schemas.py`
- 创建：`backend/app/api/dependencies.py`
- 创建：`backend/app/api/errors.py`
- 创建：`backend/app/api/auth.py`
- 创建：`backend/app/api/users.py`
- 修改：`backend/app/main.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_auth_api.py`

- [ ] **步骤 1：编写注册到退出的失败集成测试**

```python
def test_register_login_me_logout_flow(client) -> None:
    register = client.post("/auth/register", json={
        "email": "student@example.com",
        "username": "student",
        "password": "correct horse battery",
        "self_programming_level": 2,
        "self_maths_level": 4,
    })
    assert register.status_code == 201
    assert "password_hash" not in register.text
    assert "effective_programming_level" not in register.text

    login = client.post("/auth/login", json={
        "email": "student@example.com", "password": "correct horse battery",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["self_maths_level"] == 4

    assert client.post("/auth/logout", headers=headers).status_code == 204
    rejected = client.get("/users/me", headers=headers)
    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "invalid_token"
```

- [ ] **步骤 2：运行并确认 Router 缺失**

运行：`.venv/bin/python -m pytest backend/tests/test_auth_api.py -v`  
预期：FAIL，接口返回 404 或 fixture 尚不存在。

- [ ] **步骤 3：实现 Pydantic Schema、依赖与 Router**

请求模型使用 `EmailStr`、用户名正则 `^[A-Za-z0-9_.-]{3,32}$`、密码 12-128 字符、严格整数等级
1-5。统一错误响应形状：

```python
class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
```

`create_app()` 通过 `app.state.container` 保存默认装配，并允许测试传入内存 Service。注册 201、
登录 200、退出 204、当前用户 200；缺失/无效/过期 Token 均为 401。
`conftest.py` 增加 `client` fixture：每个测试创建新的 `InMemoryStore` 和 `create_app(container=...)`，
保证测试之间没有全局字典泄漏。

- [ ] **步骤 4：验证 API 和 OpenAPI**

```bash
.venv/bin/python -m pytest backend/tests/test_auth_api.py backend/tests/test_auth_service.py -v
.venv/bin/python -m ruff check backend/app/api backend/app/main.py backend/tests/test_auth_api.py
```

预期：全部 PASS；OpenAPI 包含 `/auth/register`、`/auth/login`、`/users/me`。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/api backend/app/main.py backend/tests/conftest.py backend/tests/test_auth_api.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: expose authentication API (task 5/12)"
git push
```

### 任务 6：会话创建、列表、历史和所有权 API

**文件：**
- 创建：`backend/app/services/chat.py`
- 创建：`backend/app/api/sessions.py`
- 修改：`backend/app/api/schemas.py`
- 修改：`backend/app/main.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_sessions_api.py`

- [ ] **步骤 1：编写失败的会话所有权测试**

```python
def test_sessions_are_private_and_ordered(client, register_and_login) -> None:
    first_headers = register_and_login("first@example.com", "first")
    second_headers = register_and_login("second@example.com", "second")

    created = client.post("/sessions", json={"title": "Loops"}, headers=first_headers)
    session_id = created.json()["id"]
    assert created.status_code == 201
    assert client.get("/sessions", headers=first_headers).json()[0]["id"] == session_id

    hidden = client.get(f"/sessions/{session_id}/messages", headers=second_headers)
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "session_not_found"
```

- [ ] **步骤 2：运行并确认接口 404**

运行：`.venv/bin/python -m pytest backend/tests/test_sessions_api.py -v`  
预期：FAIL，`POST /sessions` 返回 404。

- [ ] **步骤 3：实现会话 Service 与 Router**

`ChatService` 先实现三个精确公开方法：`create_session(*, user_id: UUID, title: str | None) ->
ChatSession`、`list_sessions(*, user_id: UUID) -> list[ChatSession]` 和
`list_messages(*, user_id: UUID, session_id: UUID) -> list[ChatMessage]`，三者均为 `async def`。

标题可空，非空时去除首尾空白并限制 120 字符。不存在和非所有者都抛相同
`NotFoundError("session_not_found", "Session not found")`。
`conftest.py` 增加 `register_and_login(email, username)` 工厂 fixture，密码固定使用满足 12 字符下限
的测试值，返回带 Bearer Token 的 headers。

- [ ] **步骤 4：验证会话接口**

```bash
.venv/bin/python -m pytest backend/tests/test_sessions_api.py backend/tests/test_auth_api.py -v
.venv/bin/python -m ruff check backend/app/services/chat.py backend/app/api/sessions.py backend/tests/test_sessions_api.py
```

预期：全部 PASS。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/services/chat.py backend/app/api/sessions.py backend/app/api/schemas.py backend/app/main.py backend/tests/conftest.py backend/tests/test_sessions_api.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: add protected chat sessions (task 6/12)"
git push
```

### 任务 7：Problem Analyzer 合同与确定性 Mock

**文件：**
- 创建：`backend/app/ai/analyzer.py`
- 创建：`backend/app/ai/mock_analyzer.py`
- 创建：`backend/tests/test_analyzer.py`

- [ ] **步骤 1：编写失败的 Analyzer 合同测试**

```python
import pytest


@pytest.mark.asyncio
async def test_mock_analyzer_is_deterministic_and_first_turn_is_new() -> None:
    from backend.app.ai.analyzer import AnalyzerRequest
    from backend.app.ai.mock_analyzer import MockProblemAnalyzer

    analyzer = MockProblemAnalyzer()
    request = AnalyzerRequest(user_message="Why does my loop not stop?", recent_messages=())
    first = await analyzer.analyze(request)
    second = await analyzer.analyze(request)
    assert first == second
    assert first.same_problem is False
    assert first.is_elaboration is False
    assert 1 <= first.programming_difficulty <= 5
    assert 1 <= first.maths_difficulty <= 5
```

- [ ] **步骤 2：运行并确认 Analyzer 模块缺失**

运行：`.venv/bin/python -m pytest backend/tests/test_analyzer.py -v`  
预期：FAIL，缺少 `backend.app.ai.analyzer`。

- [ ] **步骤 3：实现异步 Analyzer Protocol 和 Mock**

```python
@dataclass(frozen=True)
class AnalyzerRequest:
    user_message: str
    recent_messages: tuple[str, ...]


class ProblemAnalyzer(Protocol):
    async def analyze(self, request: AnalyzerRequest) -> ProblemAssessment: ...
```

Mock 使用固定规则：包含代码/循环关键词时编程难度 3，否则 1；数学关键词时数学难度 3，否则 1；
有历史且规范化后的当前问题与最近用户问题相同才判 `same_problem=True`。它是测试替身，不声称具备
真实语义理解。

- [ ] **步骤 4：验证 Analyzer 与 metadata 边界**

```bash
.venv/bin/python -m pytest backend/tests/test_analyzer.py backend/tests/test_pedagogy.py -v
.venv/bin/python -m ruff check backend/app/ai/analyzer.py backend/app/ai/mock_analyzer.py backend/tests/test_analyzer.py
```

预期：全部 PASS。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/ai/analyzer.py backend/app/ai/mock_analyzer.py backend/tests/test_analyzer.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: add problem analyzer boundary (task 7/12)"
git push
```

### 任务 8：异步 Tutor Provider 迁移与一次重试策略

**文件：**
- 修改：`backend/app/ai/provider.py`
- 修改：`backend/app/ai/mock_provider.py`
- 创建：`backend/app/ai/retry.py`
- 修改：`backend/app/cli.py`
- 修改：`backend/tests/test_mock_provider.py`
- 修改：`backend/tests/test_cli.py`
- 创建：`backend/tests/test_retry.py`

- [ ] **步骤 1：先把测试改为异步并添加重试测试**

```python
@pytest.mark.asyncio
async def test_mock_provider_returns_deterministic_response() -> None:
    provider = MockTutorProvider()
    request = TutorRequest(system_prompt="Programming hint level: 2/5", user_message="Why?")
    assert await provider.generate(request) == await provider.generate(request)


@pytest.mark.asyncio
async def test_retry_runs_one_retry_for_transient_error() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("temporary")
        return "ok"

    result = await retry_once(operation, is_transient=lambda exc: isinstance(exc, TimeoutError), sleep=no_sleep)
    assert result == "ok"
    assert attempts == 2
```

- [ ] **步骤 2：运行并确认同步实现导致红灯**

运行：`.venv/bin/python -m pytest backend/tests/test_mock_provider.py backend/tests/test_retry.py -v`  
预期：FAIL，不能 `await` 当前 `TutorResponse` 或缺少 `retry_once`。

- [ ] **步骤 3：迁移为异步合同并保持 CLI 兼容**

```python
class TutorProvider(Protocol):
    async def generate(self, request: TutorRequest) -> TutorResponse: ...


async def retry_once(operation, *, is_transient, sleep, delay_seconds: float = 0.25):
    try:
        return await operation()
    except Exception as exc:
        if not is_transient(exc):
            raise
        await sleep(delay_seconds)
        return await operation()
```

`MockTutorProvider.generate` 改为 `async def`。CLI 把原逻辑移入 `_run(args)`，`main()` 使用
`asyncio.run(_run(args))`；JSON 输出保持 Phase 01 完全一致。

- [ ] **步骤 4：验证 Provider、Retry 与 CLI 回归**

```bash
.venv/bin/python -m pytest backend/tests/test_mock_provider.py backend/tests/test_retry.py backend/tests/test_cli.py -v
.venv/bin/python -m ruff check backend/app/ai/provider.py backend/app/ai/mock_provider.py backend/app/ai/retry.py backend/app/cli.py
```

预期：全部 PASS；CLI 仍返回编程等级 3、数学等级 1。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/ai/provider.py backend/app/ai/mock_provider.py backend/app/ai/retry.py backend/app/cli.py backend/tests/test_mock_provider.py backend/tests/test_retry.py backend/tests/test_cli.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "refactor: make tutor providers asynchronous (task 8/12)"
git push
```

### 任务 9：原子 Chat Service 教学回合

**文件：**
- 修改：`backend/app/services/chat.py`
- 修改：`backend/app/memory.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_chat_service.py`

- [ ] **步骤 1：编写成功、失败回滚和同会话串行测试**

```python
@pytest.mark.asyncio
async def test_send_message_commits_two_messages_and_new_state(chat_service, user, session, store) -> None:
    turn = await chat_service.send_message(
        user_id=user.id, session_id=session.id, content="Why does my loop not stop?"
    )
    history = await store.messages.list_for_session(session.id)
    assert [message.role.value for message in history] == ["user", "assistant"]
    assert turn.assistant_message.provider == "mock"


@pytest.mark.asyncio
async def test_tutor_failure_leaves_no_messages_or_state_change(chat_service_with_failing_tutor, user, session, store) -> None:
    before = await store.users.get(user.id)
    with pytest.raises(Exception):
        await chat_service_with_failing_tutor.send_message(
            user_id=user.id, session_id=session.id, content="Help"
        )
    assert await store.messages.list_for_session(session.id) == []
    assert await store.users.get(user.id) == before
```

- [ ] **步骤 2：运行并确认 `send_message` 尚不存在**

运行：`.venv/bin/python -m pytest backend/tests/test_chat_service.py -v`  
预期：FAIL，`ChatService` 没有 `send_message`。

- [ ] **步骤 3：实现完整原子数据流**

`send_message` 必须在会话锁内依次执行：所有权 → 最近 10 条/4,000 字符历史 → Analyzer →
`coerce_pedagogy_metadata` → `compute_hint_levels` → 两次 `update_effective_level` →
`build_system_prompt` → Tutor → Unit of Work commit。返回：

```python
@dataclass(frozen=True)
class ChatTurn:
    user_message: ChatMessage
    assistant_message: ChatMessage
```

不得把 `ProblemAssessment`、提示等级、有效能力值或系统 Prompt 放入公开响应。Analyzer/Tutor 最终
失败时不得调用 `uow.commit()`。
`conftest.py` 增加成功与失败 Provider/Analyzer fixtures；失败替身抛稳定领域异常，不使用网络。

- [ ] **步骤 4：验证原子性与教学回归**

```bash
.venv/bin/python -m pytest backend/tests/test_chat_service.py backend/tests/test_pedagogy.py backend/tests/test_prompt_builder.py -v
.venv/bin/python -m ruff check backend/app/services/chat.py backend/app/memory.py backend/tests/test_chat_service.py
```

预期：成功、Analyzer 失败、Tutor 失败和并发串行测试全部 PASS。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/services/chat.py backend/app/memory.py backend/tests/conftest.py backend/tests/test_chat_service.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: orchestrate atomic tutoring turns (task 9/12)"
git push
```

### 任务 10：聊天 API、错误映射与学生可见响应

**文件：**
- 修改：`backend/app/api/sessions.py`
- 修改：`backend/app/api/schemas.py`
- 修改：`backend/app/api/errors.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_chat_api.py`

- [ ] **步骤 1：编写完整聊天 API 和泄露防护测试**

```python
def test_chat_api_returns_visible_messages_without_hidden_state(client, logged_in_session) -> None:
    headers, session_id = logged_in_session
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "Why does my loop not stop?"},
        headers=headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["user_message"]["role"] == "user"
    assert payload["assistant_message"]["role"] == "assistant"
    serialized = response.text
    for hidden in ("effective_", "hint_level", "problem_assessment", "system_prompt"):
        assert hidden not in serialized


def test_upstream_failure_uses_stable_safe_error(client_with_failing_tutor, logged_in_session) -> None:
    headers, session_id = logged_in_session
    response = client_with_failing_tutor.post(
        f"/sessions/{session_id}/messages", json={"content": "Help"}, headers=headers
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "upstream_unavailable"
```

- [ ] **步骤 2：运行并确认消息接口 404 或 405**

运行：`.venv/bin/python -m pytest backend/tests/test_chat_api.py -v`  
预期：FAIL，聊天 POST 路由尚不存在。

- [ ] **步骤 3：实现公开 Schema 和错误映射**

`MessageCreate.content` 为去除空白后的 1-4,000 字符。`ChatTurnResponse` 只包含 `session_id`、
`user_message`、`assistant_message`；公开 Message 只含 `id`、`role`、`content`、`created_at`、
助手的 `provider`/`model`。映射：无效上游结构 502，瞬时故障重试后失败 503，未预期错误 500。
`conftest.py` 增加 `logged_in_session` 与 `client_with_failing_tutor`，两者各自使用全新的内存容器。

- [ ] **步骤 4：验证聊天 API 与所有集成路径**

```bash
.venv/bin/python -m pytest backend/tests/test_chat_api.py backend/tests/test_sessions_api.py backend/tests/test_auth_api.py -v
.venv/bin/python -m ruff check backend/app/api backend/tests/test_chat_api.py
```

预期：全部 PASS。

- [ ] **步骤 5：存档并提交**

```bash
git add backend/app/api/sessions.py backend/app/api/schemas.py backend/app/api/errors.py backend/tests/conftest.py backend/tests/test_chat_api.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: expose atomic tutoring chat API (task 10/12)"
git push
```

### 任务 11：OpenAI Responses API Adapter 与真实冒烟测试

**文件：**
- 创建：`backend/app/ai/openai_adapters.py`
- 修改：`backend/app/main.py`
- 创建：`backend/tests/test_openai_adapters.py`
- 创建：`backend/tests/test_openai_live.py`
- 修改：`pyproject.toml`
- 修改：`.gitignore`
- 创建：`.env.example`

- [ ] **步骤 1：编写不联网的 SDK Adapter 合同测试**

```python
@pytest.mark.asyncio
async def test_openai_analyzer_maps_structured_result(fake_openai_client) -> None:
    fake_openai_client.analysis = {
        "programming_difficulty": 3,
        "maths_difficulty": 1,
        "same_problem": False,
        "is_elaboration": False,
    }
    analyzer = OpenAIProblemAnalyzer(client=fake_openai_client, model="gpt-5.6-luna")
    result = await analyzer.analyze(AnalyzerRequest(user_message="Why?", recent_messages=()))
    assert result.programming_difficulty == 3
    assert fake_openai_client.last_request["model"] == "gpt-5.6-luna"


@pytest.mark.asyncio
async def test_openai_tutor_maps_output_text_and_usage(fake_openai_client) -> None:
    provider = OpenAITutorProvider(client=fake_openai_client, model="gpt-5.6-terra")
    result = await provider.generate(TutorRequest(system_prompt="Teach", user_message="Why?"))
    assert result.provider == "openai"
    assert result.model == "gpt-5.6-terra"
    assert result.input_tokens > 0
```

- [ ] **步骤 2：运行并确认 Adapter 缺失**

运行：`.venv/bin/python -m pytest backend/tests/test_openai_adapters.py -v`  
预期：FAIL，缺少 `backend.app.ai.openai_adapters`。

- [ ] **步骤 3：实现 OpenAI Adapter 和应用装配**

使用 `AsyncOpenAI` 与 Responses API。Analyzer 使用严格 Pydantic Schema；Tutor 将系统 Prompt 传
`instructions`，学生文本传 `input`，读取 `response.output_text` 和 usage。模型、reasoning effort、
timeout 全部来自 `Settings`。SDK 身份验证/请求错误不重试；连接、超时、限流、5xx 使用任务 8 的
一次重试策略，再映射为稳定领域错误。

`.env.example` 只能包含：

```dotenv
APP_PROVIDER_MODE=mock
OPENAI_API_KEY=
OPENAI_ANALYZER_MODEL=gpt-5.6-luna
OPENAI_TUTOR_MODEL=gpt-5.6-terra
OPENAI_REASONING_EFFORT=medium
OPENAI_TIMEOUT_SECONDS=30
AUTH_TOKEN_TTL_SECONDS=86400
```

`.gitignore` 增加精确规则 `.env`；不得使用会误伤 `.env.example` 的 `.env*`。

- [ ] **步骤 4：运行离线 Adapter 测试**

```bash
.venv/bin/python -m pytest backend/tests/test_openai_adapters.py backend/tests/test_config.py -v
.venv/bin/python -m ruff check backend/app/ai/openai_adapters.py backend/tests/test_openai_adapters.py
```

预期：全部 PASS；没有网络请求。

- [ ] **步骤 5：此时才由用户创建和配置 API Key**

1. 打开 OpenAI Platform 的 API Keys 页面，创建权限受限、可撤销的项目 Key。
2. 不把 Key 粘贴到聊天；在本机终端会话中设置 `OPENAI_API_KEY`。
3. 设置 `APP_PROVIDER_MODE=openai`。
4. 运行秘密扫描，确认 Git diff 和 staged files 中没有 Key。
5. 运行显式 live marker：

```bash
.venv/bin/python -m pytest -m openai_live backend/tests/test_openai_live.py -v
```

预期：若账户开放所选模型且额度可用，Analyzer 和 Tutor 各完成一次调用；否则报告真实账户/模型错误，
不改成伪成功，也不阻塞默认离线套件。

- [ ] **步骤 6：存档并提交（绝不提交 `.env`）**

```bash
git add .gitignore .env.example pyproject.toml backend/app/ai/openai_adapters.py backend/app/main.py backend/tests/test_openai_adapters.py backend/tests/test_openai_live.py docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "feat: add optional OpenAI adapters (task 11/12)"
git push
```

### 任务 12：运行文档、阶段验收和完整验证

**文件：**
- 创建：`docs/08-fastapi-memory-backend.md`
- 修改：`README.md`
- 修改：`docs/prompts/development/phase-02a-fastapi-memory.md`
- 必要时修改：`docs/diagrams/08-phase-02a-architecture.mmd`
- 必要时修改：`docs/diagrams/09-phase-02a-api-and-data.mmd`
- 必要时修改：`docs/diagrams/10-phase-02a-chat-transaction.mmd`
- 必要时修改对应：`docs/diagrams/rendered/*.svg`

- [ ] **步骤 1：编写真实运行说明**

文档必须包含：Python 3.11+ 环境、安装命令、Mock 启动命令、`/docs` 注册到聊天操作、OpenAI 配置
但不含真实 Key、错误码、重启清空说明、测试命令、Phase 02B 交接和本阶段已知限制。

- [ ] **步骤 2：运行 Mock 服务人工冒烟**

```bash
APP_PROVIDER_MODE=mock .venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

另一个终端按顺序请求 `/health`、注册、登录、创建会话、发送消息、读取历史、退出。预期所有成功
状态与规格一致，退出后的 Token 返回 401；不得把 Token 写入受版本控制文件。

- [ ] **步骤 3：运行全套自动验证**

```bash
.venv/bin/python -m pytest backend/tests -v -m "not openai_live"
.venv/bin/python -m ruff check backend
git diff --check
```

预期：0 failures，Ruff 输出 `All checks passed!`，diff check 无输出。

- [ ] **步骤 4：执行秘密和图表存档检查**

```bash
rg -n "sk-[A-Za-z0-9_-]{20,}|gh[opsu]_[A-Za-z0-9]{20,}" . --glob '!*.svg' --glob '!.git/**' --glob '!.venv/**'
test -s docs/diagrams/rendered/08-phase-02a-architecture.svg
test -s docs/diagrams/rendered/09-phase-02a-api-and-data.svg
test -s docs/diagrams/rendered/10-phase-02a-chat-transaction.svg
```

预期：秘密扫描 0 matches；3 个 SVG 均非空。

- [ ] **步骤 5：完成学习验收**

学习者需用自己的话回答并存档：

1. 为什么 Router 不应直接操作内存字典？
2. 为什么 OpenAI Analyzer 的 JSON 仍是不可信输入？
3. 为什么一轮聊天必须在 Tutor 成功后才提交？
4. Mock 与真实 Provider 分别在哪些测试中使用？
5. Phase 02B 为什么可以替换 Repository 而不重写 Router？

- [ ] **步骤 6：提交、推送并进入分支收尾**

```bash
git add README.md docs/08-fastapi-memory-backend.md docs/diagrams docs/prompts/development/phase-02a-fastapi-memory.md
git commit -m "docs: complete phase 02a acceptance (task 12/12)"
git push
```

随后重新验证本地与远端哈希一致，使用 `requesting-code-review` 审查实现，再使用
`finishing-a-development-branch` 提供本地合并、创建 PR、保留分支或丢弃工作的选择。
