from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    session_id: str = Field(..., description="会话唯一 ID（前端生成并复用）")
    student_id: int = Field(..., gt=0, description="当前学生 ID")
    message: str = Field(..., min_length=1, description="用户输入")


class AgentChatResponse(BaseModel):
    reply: str
