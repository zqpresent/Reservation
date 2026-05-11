import logging
from collections import defaultdict
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from clients.backend_client import BackendAPIError, BackendClient
from prompts import build_system_prompt
from stores.history_store import HistoryStore
from tools.student_tools import build_student_tools

logger = logging.getLogger("reservation-agent")


def _message_to_text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
        return "\n".join(x for x in chunks if x)
    return str(content)


class AgentService:
    def __init__(
        self,
        *,
        backend_client: BackendClient,
        model_name: str,
        api_key: str,
        base_url: str | None,
        model_timeout_seconds: float = 30,
        model_max_retries: int = 2,
        max_history_turns: int = 8,
        history_store_dir: str = ".agent_history",
    ):
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY 未配置，无法启动 AgentService。请在 code/agent/.env 中配置，"
                "或确保 .env.example 中存在该变量。"
            )
        self.backend_client = backend_client
        self.max_history_turns = max_history_turns
        self._history: dict[str, list[BaseMessage]] = defaultdict(list)
        self.history_store = HistoryStore(history_store_dir)
        self.model = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.2,
            timeout=model_timeout_seconds,
            max_retries=model_max_retries,
        )

    async def chat(self, *, session_id: str, student_id: int, message: str) -> str:
        tools = build_student_tools(self.backend_client, student_id)
        system_prompt = build_system_prompt(tools, student_id)
        agent = create_react_agent(
            model=self.model,
            tools=tools,
            prompt=system_prompt,
        )

        history = self._history.get(session_id)
        if not history:
            history = self.history_store.load(session_id)
            self._history[session_id] = history
        trace_id = uuid4().hex[:12]
        logger.info(
            "agent_chat_start trace_id=%s session_id=%s student_id=%s",
            trace_id,
            session_id,
            student_id,
        )

        try:
            result = await agent.ainvoke({"messages": [*history, HumanMessage(content=message)]})
            messages = result.get("messages", [])
            ai_message = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
            if ai_message is None:
                reply = "我暂时没有得到可用结果，请稍后再试。"
            else:
                reply = _message_to_text(ai_message).strip() or "我已处理完成。"
        except BackendAPIError as exc:
            logger.warning(
                "agent_chat_backend_error trace_id=%s status=%s detail=%s",
                trace_id,
                exc.status_code,
                exc.detail,
            )
            reply = f"后端接口调用失败（{exc.status_code}）：{exc.detail}。请稍后重试。"
        except Exception as exc:
            logger.exception("agent_chat_unexpected_error trace_id=%s error=%s", trace_id, exc)
            reply = "当前助手暂时不可用，请稍后重试。"

        history.extend([HumanMessage(content=message), AIMessage(content=reply)])
        max_messages = self.max_history_turns * 2
        if len(history) > max_messages:
            self._history[session_id] = history[-max_messages:]
            history = self._history[session_id]
        self.history_store.save(session_id, history)

        logger.info(
            "agent_chat_done trace_id=%s session_id=%s history_size=%s",
            trace_id,
            session_id,
            len(self._history.get(session_id, [])),
        )
        return reply

    def get_session_history(self, session_id: str, limit: int = 50) -> list[dict]:
        return self.history_store.get_ui_history(session_id, limit=limit)

    async def ready(self) -> tuple[bool, str]:
        try:
            await self.backend_client.health()
            return True, "ok"
        except Exception as exc:
            return False, f"backend_unavailable: {exc}"
