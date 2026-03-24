from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import database
import models
import schemas
import auth as auth_utils

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=schemas.StudentInfo, summary="学生注册")
def register(body: schemas.StudentRegister, db: Session = Depends(database.get_db)):
    if db.query(models.Student).filter(models.Student.student_no == body.student_no).first():
        raise HTTPException(status_code=400, detail="该学号已注册")
    student = models.Student(
        student_no=body.student_no,
        password=auth_utils.hash_password(body.password),
        name=body.name,
        email=body.email,
        department=body.department,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.post("/login", response_model=schemas.Token, summary="学生登录")
def student_login(body: schemas.StudentLogin, db: Session = Depends(database.get_db)):
    student = db.query(models.Student).filter(models.Student.student_no == body.student_no).first()
    if not student or not auth_utils.verify_password(body.password, student.password):
        raise HTTPException(status_code=401, detail="学号或密码错误")
    token = auth_utils.create_token({"sub": student.id, "type": "student"})
    return {"access_token": token, "token_type": "bearer", "user_type": "student", "student_id": student.id}


@router.post("/admin/register", response_model=schemas.AdminInfo, summary="管理员注册（demo阶段开放）")
def admin_register(body: schemas.AdminRegister, db: Session = Depends(database.get_db)):
    if db.query(models.AdminUser).filter(models.AdminUser.username == body.username).first():
        raise HTTPException(status_code=400, detail="该用户名已注册")
    role = body.role if body.role in ["super_admin", "room_admin", "normal_admin"] else "normal_admin"
    admin = models.AdminUser(
        username=body.username,
        password=auth_utils.hash_password(body.password),
        name=body.name,
        role=role,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@router.post("/admin/login", response_model=schemas.Token, summary="管理员登录")
def admin_login(body: schemas.AdminLogin, db: Session = Depends(database.get_db)):
    admin = db.query(models.AdminUser).filter(models.AdminUser.username == body.username).first()
    if not admin or not auth_utils.verify_password(body.password, admin.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = auth_utils.create_token({"sub": admin.id, "type": "admin", "role": admin.role.value})
    return {
        "access_token": token, "token_type": "bearer", "user_type": "admin",
        "admin_id": admin.id, "admin_role": admin.role.value, "admin_name": admin.name
    }


@router.get("/me", response_model=schemas.StudentInfo, summary="获取当前学生信息")
def get_me(student_id: int = Query(...), db: Session = Depends(database.get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="用户不存在")
    return student


@router.get("/admin/me", response_model=schemas.AdminInfo, summary="获取当前管理员信息")
def get_admin_me(current: models.AdminUser = Depends(auth_utils.get_current_admin)):
    return current
