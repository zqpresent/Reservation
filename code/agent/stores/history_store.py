import json
import re
from pathlib import Path
from threading import Lock

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class HistoryStore:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _safe_session_id(self, session_id: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9._-]", "_", session_id.strip())
        return value or "default"

    def _file_path(self, session_id: str) -> Path:
        return self.root / f"{self._safe_session_id(session_id)}.json"

    def load(self, session_id: str) -> list[BaseMessage]:
        path = self._file_path(session_id)
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            messages: list[BaseMessage] = []
            for item in payload:
                mtype = item.get("type")
                content = str(item.get("content", ""))
                if not content:
                    continue
                if mtype == "human":
                    messages.append(HumanMessage(content=content))
                elif mtype == "ai":
                    messages.append(AIMessage(content=content))
            return messages
        except Exception:
            return []

    def save(self, session_id: str, messages: list[BaseMessage]):
        path = self._file_path(session_id)
        payload = []
        for message in messages:
            if isinstance(message, HumanMessage):
                payload.append({"type": "human", "content": str(message.content)})
            elif isinstance(message, AIMessage):
                payload.append({"type": "ai", "content": str(message.content)})
        with self._lock:
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

    def get_ui_history(self, session_id: str, limit: int = 50) -> list[dict]:
        messages = self.load(session_id)
        rows = []
        for m in messages[-max(1, limit):]:
            role = "user" if isinstance(m, HumanMessage) else "assistant"
            rows.append({"role": role, "content": str(m.content)})
        return rows
