from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, rooms, seats, reservations, notifications, rbac, system, stats
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
        seed_defaults(db)
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
app.include_router(notifications.router)
app.include_router(rbac.router)
app.include_router(system.router)
app.include_router(stats.router)


@app.get("/", tags=["健康检查"])
def root():
    return {"status": "ok", "message": "自习座位预约系统后端运行中"}


def seed_defaults(db):
    permissions = [
        ("room.read", "查看自习室", "room", "read"),
        ("room.write", "管理自习室", "room", "write"),
        ("seat.write", "管理座位", "seat", "write"),
        ("reservation.read", "查看预约", "reservation", "read"),
        ("reservation.write", "管理预约", "reservation", "write"),
        ("violation.read", "查看违约", "violation", "read"),
        ("rbac.write", "管理角色权限", "rbac", "write"),
        ("system.write", "管理系统参数", "system", "write"),
        ("stats.read", "查看统计", "stats", "read"),
        ("admin_user.write", "管理管理员账号", "admin_user", "write"),
    ]
    roles = [
        ("super_admin", "超级管理员"),
        ("room_admin", "教室管理员"),
        ("normal_admin", "普通管理员"),
    ]

    perm_map = {}
    for code, name, resource, action in permissions:
        item = db.query(models.Permission).filter(models.Permission.code == code).first()
        if not item:
            item = models.Permission(code=code, name=name, resource=resource, action=action)
            db.add(item)
            db.flush()
        perm_map[code] = item

    role_map = {}
    for key, name in roles:
        role = db.query(models.Role).filter(models.Role.key == key).first()
        if not role:
            role = models.Role(key=key, name=name, is_active=1)
            db.add(role)
            db.flush()
        role_map[key] = role

    role_perms = {
        "super_admin": list(perm_map.keys()),
        "room_admin": ["room.read", "room.write", "seat.write", "reservation.read", "violation.read", "stats.read"],
        "normal_admin": ["reservation.read", "reservation.write", "violation.read", "stats.read"],
    }
    for role_key, codes in role_perms.items():
        role = role_map[role_key]
        existing = {
            rp.permission_id
            for rp in db.query(models.RolePermission).filter(models.RolePermission.role_id == role.id).all()
        }
        for code in codes:
            perm_id = perm_map[code].id
            if perm_id not in existing:
                db.add(models.RolePermission(role_id=role.id, permission_id=perm_id))

    # 绑定管理员默认角色
    admins = db.query(models.AdminUser).all()
    for admin in admins:
        role_key = admin.role.value if hasattr(admin.role, "value") else str(admin.role)
        role = role_map.get(role_key) or role_map["normal_admin"]
        has_binding = db.query(models.AdminUserRole).filter(
            models.AdminUserRole.admin_id == admin.id,
            models.AdminUserRole.role_id == role.id,
        ).first()
        if not has_binding:
            db.add(models.AdminUserRole(admin_id=admin.id, role_id=role.id))

    params = [
        ("MAX_RESERVE_HOURS", os.getenv("MAX_RESERVE_HOURS", "4"), "单次最大预约小时数"),
        ("CHECKIN_TIMEOUT_MINUTES", os.getenv("CHECKIN_TIMEOUT_MINUTES", "15"), "签到超时自动取消分钟数"),
        ("REMIND_BEFORE_MINUTES", os.getenv("REMIND_BEFORE_MINUTES", "15"), "预约开始前提醒分钟数"),
        ("REMIND_AFTER_START_MINUTES", os.getenv("REMIND_AFTER_START_MINUTES", "10"), "预约开始后未签到提醒分钟数"),
    ]
    for key, value, desc in params:
        item = db.query(models.SystemParam).filter(models.SystemParam.key == key).first()
        if not item:
            db.add(models.SystemParam(key=key, value=str(value), description=desc))
    db.commit()
