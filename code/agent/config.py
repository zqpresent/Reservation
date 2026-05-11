import os

from dotenv import load_dotenv

# 优先读取 .env，若不存在则回退到 .env.example（方便本地快速启动）
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv(".env.example")


class Settings:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_base_url = os.getenv("OPENAI_BASE_URL")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
        self.openai_max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
        self.backend_base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
        self.backend_timeout_seconds = float(os.getenv("BACKEND_TIMEOUT_SECONDS", "15"))
        self.max_history_turns = int(os.getenv("MAX_HISTORY_TURNS", "8"))
        self.history_store_dir = os.getenv("HISTORY_STORE_DIR", ".agent_history")


settings = Settings()
