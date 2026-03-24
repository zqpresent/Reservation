from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, rooms, seats, reservations
from scheduler import start_scheduler
import models
import os
from dotenv import load_dotenv

load_dotenv()

# 初始化数据库表（如果不存在则创建）
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database import SessionLocal
    from auth import hash_password
    db = SessionLocal()
    try:
        admin = db.query(models.AdminUser).filter(models.AdminUser.username == "admin").first()
        if admin and admin.password.startswith("$2b$12$placeholder"):
            init_password = os.getenv("INIT_ADMIN_PASSWORD", "admin123")
            admin.password = hash_password(init_password)
            db.commit()
            print("[启动] 超级管理员密码已初始化")
    finally:
        db.close()
    start_scheduler()
    print("[启动] 定时任务已启动")
    yield


app = FastAPI(
    title="自习座位预约系统 API",
    description="后端接口文档，访问 /docs 查看完整 Swagger UI",
    version="0.1.0",
    lifespan=lifespan,
)

# 跨域配置（允许前端开发时的本地端口访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(seats.router)
app.include_router(reservations.router)


@app.get("/", tags=["健康检查"])
def root():
    return {"status": "ok", "message": "自习座位预约系统后端运行中"}
