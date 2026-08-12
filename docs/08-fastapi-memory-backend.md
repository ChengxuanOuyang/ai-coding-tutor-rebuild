# Phase 02A FastAPI 内存后端运行手册

Phase 02A 把 Phase 01 的教学核心接入一个可运行的 FastAPI 后端。它支持注册、登录、
受保护会话、聊天回合、Mock Provider 和可选 OpenAI Provider。当前阶段仍使用内存
Repository，重启服务会清空所有用户、Token、会话和消息。

## 环境要求

- Python 3.11 或更高版本。
- 本地虚拟环境 `.venv`。
- 默认 Mock 模式不需要 API Key，不依赖网络。
- OpenAI 模式需要你在本机 Shell 中设置 `OPENAI_API_KEY`，不要把真实 Key 写进聊天、代码、
  测试快照、日志或 Git。

## 安装

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

如果虚拟环境已经存在，可以直接运行安装命令刷新依赖。

## Mock 模式启动

Mock 是默认 Provider，也是自动测试和本地教学流程演示的推荐入口。

```bash
APP_PROVIDER_MODE=mock .venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

启动后访问：

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/docs`

`/docs` 是 FastAPI 自动生成的 OpenAPI 页面，可以按顺序完成注册、登录、创建会话、
发送消息、读取历史和退出。

## OpenAI 模式配置

`.env.example` 只保存空模板和值示例，真实 Key 必须留在本机环境变量里。

```bash
export APP_PROVIDER_MODE=openai
export OPENAI_API_KEY='replace-with-your-local-key'
export OPENAI_ANALYZER_MODEL=gpt-5.6-luna
export OPENAI_TUTOR_MODEL=gpt-5.6-terra
export OPENAI_REASONING_EFFORT=medium
export OPENAI_TIMEOUT_SECONDS=30
export AUTH_TOKEN_TTL_SECONDS=86400
.venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

实际操作时不要把 Key 发到聊天里。更安全的 zsh 输入方式是：

```bash
read -s "OPENAI_API_KEY?OpenAI API Key: "
export OPENAI_API_KEY
echo
```

OpenAI Adapter 的边界：

- Analyzer 使用 Responses API 的结构化输出，把题目评估解析为四字段
  `ProblemAssessment`。
- Tutor 使用 `instructions` 传入系统 Prompt，使用 `input` 传入学生消息。
- SDK 内部重试关闭；后端只对连接、超时、限流和 5xx 错误重试一次。
- 认证、权限、请求格式和无效结构化响应不会重试。
- OpenAI 返回的 JSON 仍然是不可信输入，必须经过 Pydantic、领域模型和教学规则校验后才可使用。

## 接口流程

### 1. 健康检查

```bash
curl -s http://127.0.0.1:8000/health
```

预期：

```json
{"status":"ok"}
```

### 2. 注册

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "student@example.com",
    "username": "student_one",
    "password": "correct horse battery staple",
    "self_programming_level": 2,
    "self_maths_level": 3
  }'
```

### 3. 登录

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "student@example.com",
    "password": "correct horse battery staple"
  }' | .venv/bin/python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```

Token 只应保存在当前 Shell 变量里，不要写入受版本控制文件。

### 4. 创建会话

```bash
SESSION_ID=$(curl -s -X POST http://127.0.0.1:8000/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title": "Python loop help"}' \
  | .venv/bin/python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
```

### 5. 发送消息

```bash
curl -s -X POST "http://127.0.0.1:8000/sessions/$SESSION_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"content": "My Python for loop never stops. What should I inspect first?"}'
```

Mock 模式会返回确定性的教学回复。它用于验证完整工作流，不代表真实模型质量。

### 6. 读取历史

```bash
curl -s "http://127.0.0.1:8000/sessions/$SESSION_ID/messages" \
  -H "Authorization: Bearer $TOKEN"
```

预期返回按创建时间排序的用户消息和助手消息。公开响应不会包含隐藏提示等级、能力值、
Analyzer 评估、系统 Prompt 或 Token 用量。

### 7. 退出并验证 Token 失效

```bash
curl -i -X POST http://127.0.0.1:8000/auth/logout \
  -H "Authorization: Bearer $TOKEN"

curl -i "http://127.0.0.1:8000/sessions" \
  -H "Authorization: Bearer $TOKEN"
```

退出接口预期返回 `204`。退出后再次使用同一个 Token 访问受保护接口，预期返回 `401`。

## 错误码

| HTTP 状态 | code | 含义 |
| --- | --- | --- |
| 401 | `invalid_token` 或稳定认证错误 | 缺失、过期、未知或已撤销 Token，或登录凭证无效 |
| 404 | `session_not_found` | 会话不存在，或不属于当前用户 |
| 409 | `user_conflict` | 邮箱或用户名已被注册 |
| 422 | `validation_error` | 请求体、路径参数或字段约束不合法 |
| 502 | `invalid_analyzer_response` / `invalid_tutor_response` | 上游返回格式不可信或不符合合同 |
| 503 | `analyzer_unavailable` / `tutor_unavailable` | 上游暂时不可用，重试后仍失败 |
| 500 | `internal_error` | 未预期错误；响应不会泄露异常细节 |

## 验证命令

默认离线验证：

```bash
.venv/bin/python -m pytest backend/tests -v -m "not openai_live"
.venv/bin/python -m ruff check backend
git diff --check
```

秘密与图表检查：

```bash
rg -n "sk-[A-Za-z0-9_-]{20,}|gh[opsu]_[A-Za-z0-9]{20,}" . --glob '!*.svg' --glob '!.git/**' --glob '!.venv/**'
test -s docs/diagrams/rendered/08-phase-02a-architecture.svg
test -s docs/diagrams/rendered/09-phase-02a-api-and-data.svg
test -s docs/diagrams/rendered/10-phase-02a-chat-transaction.svg
```

真实 OpenAI live 测试必须显式启用，并且只在本机环境变量已经配置后运行：

```bash
APP_PROVIDER_MODE=openai .venv/bin/python -m pytest backend/tests/test_openai_live.py -m openai_live -v
```

不要把 live 测试输出中的 Key、Token 或完整请求内容写入文档。

## Phase 02B 交接

Phase 02B 可以把内存 Repository 替换成 PostgreSQL Repository，而不重写 Router，原因是：

- Router 只处理 HTTP 请求、响应模型和依赖注入。
- Service 只依赖 Repository Protocol，不依赖具体字典或数据库实现。
- Unit of Work 已经把「一轮聊天成功后再提交」建成显式边界。
- 领域模型、错误码、Provider 合同和 Prompt Builder 与存储技术解耦。

Phase 02A 已知限制：

- 重启服务会清空所有状态。
- Token 只存在内存中，没有跨进程共享。
- 没有 PostgreSQL migration、连接池或事务隔离级别。
- 没有前端、流式响应、Notebook 上下文上传和 CI/CD。
- Mock Analyzer 只按固定关键词判断难度，不具备真实语义理解。
