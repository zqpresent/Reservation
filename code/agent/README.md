# Agent Service（独立服务）

该目录提供一个与 `backend` 同级的独立 Agent 服务，基于：

- FastAPI（HTTP 服务）
- LangGraph（Agent 编排）
- LangChain OpenAI 接口（OpenAI 兼容格式）

## 1. 功能范围

当前内置 4 个工具：

1. `search_seats`：搜索可用座位
2. `my_reservations`：查询我的预约
3. `create_reservation`：创建预约
4. `cancel_reservation`：取消预约

工具调用全部转发到现有 backend API，不直连数据库。

会话上下文缓存：

- 服务会按 `session_id` 持久化聊天历史到 `HISTORY_STORE_DIR`（默认 `.agent_history`）
- Agent 重启后仍可恢复上下文
- 学生端 `chat.html` 会读取历史并回显

## 2. Agent 如何知道工具

Agent 并不是仅依赖 `SYSTEM_PROMPT` 认识工具，而是通过 `create_react_agent(model, tools, prompt)` 绑定：

1. `tools/student_tools.py` 里每个 `@tool` 的函数名、参数签名、docstring 会被转为工具 schema。  
2. LangGraph 在运行时把工具 schema 传给模型（OpenAI tool-calling 格式）。  
3. `service.py` 还会动态生成“工具目录提示词”（自动列出工具名和说明）并拼接到系统提示词，提升模型选工具稳定性。  

因此：**工具描述不必手写在固定 prompt 里**，会由工具定义自动注入。

## 3. 启动方式

```bash
cd code/agent
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填 OPENAI_API_KEY / OPENAI_BASE_URL（如需要）
# 默认端口 8100（与 backend 8000 分离）
./start.sh
```

生产部署建议：

- 以 `uvicorn main:app --host 0.0.0.0 --port 8100 --workers 2` 运行
- 反向代理（Nginx）转发 `/chat`、`/health`、`/ready`
- 为 Agent 服务单独配置日志采集

Docker 部署：

```bash
cd code/agent
docker build -t reservation-agent .
docker run --rm -p 8100:8100 --env-file .env reservation-agent
```

## 4. 接口

### `GET /health`

健康检查。

### `GET /ready`

就绪检查：会探测 backend 可用性。

### `POST /chat`

请求体：

```json
{
  "session_id": "demo-session-1",
  "student_id": 1,
  "message": "帮我找今晚19点到21点有插座的座位"
}
```

响应体：

```json
{
  "reply": "..."
}
```

### `GET /sessions/{session_id}/history?limit=30`

读取指定会话的历史消息（用于前端回显与排查）。

## 5. 目录说明

```text
agent/
├── main.py
├── service.py
├── prompts.py
├── config.py
├── schemas.py
├── clients/
│   └── backend_client.py
├── tools/
│   └── student_tools.py
├── requirements.txt
└── .env.example
```
