import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import database
import models
import os

load_dotenv(override=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

JWT_SECRET = "dev_secret_for_testing"  # demo 阶段固定值，避免环境变量加载顺序问题
JWT_EXPIRE_MINUTES = 480
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")


def get_current_student(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.Student:
    payload = decode_token(token)
    if payload.get("type") != "student":
        raise HTTPException(status_code=403, detail="需要学生身份")
    student = db.query(models.Student).filter(models.Student.id == payload.get("sub")).first()
    if not student:
        raise HTTPException(status_code=401, detail="用户不存在")
    return student


def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.AdminUser:
    payload = decode_token(token)
    if payload.get("type") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员身份")
    admin = db.query(models.AdminUser).filter(models.AdminUser.id == payload.get("sub")).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="管理员不存在或已禁用")
    return admin


def require_role(*roles: str):
    """角色权限装饰器，用法: Depends(require_role('super_admin', 'room_admin'))"""
    def checker(admin: models.AdminUser = Depends(get_current_admin)):
        if admin.role.value not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return admin
    return checker
