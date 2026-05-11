from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clients.backend_client import BackendClient
from config import settings
from schemas import AgentChatRequest, AgentChatResponse
from service import AgentService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend_client = BackendClient(settings.backend_base_url, timeout_seconds=settings.backend_timeout_seconds)
    app.state.agent_service = AgentService(
        backend_client=backend_client,
        model_name=settings.openai_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model_timeout_seconds=settings.openai_timeout_seconds,
        model_max_retries=settings.openai_max_retries,
        max_history_turns=settings.max_history_turns,
        history_store_dir=settings.history_store_dir,
    )
    try:
        yield
    finally:
        await backend_client.aclose()


app = FastAPI(
    title="Reservation Agent Service",
    description="独立智能助手服务（OpenAI compatible + LangGraph）",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent"}


@app.get("/ready")
async def ready():
    ok, detail = await app.state.agent_service.ready()
    return {"status": "ok" if ok else "not_ready", "service": "agent", "detail": detail}


@app.post("/chat", response_model=AgentChatResponse)
async def chat(body: AgentChatRequest):
    reply = await app.state.agent_service.chat(
        session_id=body.session_id,
        student_id=body.student_id,
        message=body.message,
    )
    return AgentChatResponse(reply=reply)


@app.get("/sessions/{session_id}/history")
async def get_history(session_id: str, limit: int = 50):
    rows = app.state.agent_service.get_session_history(session_id=session_id, limit=limit)
    return {"session_id": session_id, "count": len(rows), "messages": rows}
