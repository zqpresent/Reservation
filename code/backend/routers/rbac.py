from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import database
import models
import schemas

router = APIRouter(prefix="/rbac", tags=["RBAC"])


@router.get("/permissions", response_model=list[schemas.PermissionInfo], summary="权限点列表")
def list_permissions(
    db: Session = Depends(database.get_db),
):
    return db.query(models.Permission).order_by(models.Permission.code.asc()).all()


@router.get("/roles", response_model=list[schemas.RoleInfo], summary="角色列表")
def list_roles(
    db: Session = Depends(database.get_db),
):
    return db.query(models.Role).order_by(models.Role.id.asc()).all()


@router.post("/roles", response_model=schemas.RoleInfo, summary="创建角色")
def create_role(
    body: schemas.RoleCreate,
    db: Session = Depends(database.get_db),
):
    existing = db.query(models.Role).filter(models.Role.key == body.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色 key 已存在")
    role = models.Role(key=body.key, name=body.name, is_active=1)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/roles/{role_id}", response_model=schemas.RoleInfo, summary="更新角色")
def update_role(
    role_id: int,
    body: schemas.RoleUpdate,
    db: Session = Depends(database.get_db),
):
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    data = body.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


@router.put("/roles/{role_id}/permissions", response_model=dict, summary="设置角色权限")
def set_role_permissions(
    role_id: int,
    body: schemas.RolePermissionUpdate,
    db: Session = Depends(database.get_db),
):
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    db.query(models.RolePermission).filter(models.RolePermission.role_id == role_id).delete()
    for permission_id in body.permission_ids:
        exists = db.query(models.Permission).filter(models.Permission.id == permission_id).first()
        if exists:
            db.add(models.RolePermission(role_id=role_id, permission_id=permission_id))
    db.commit()
    return {"message": "角色权限已更新"}


@router.get("/admin-users", response_model=list[schemas.AdminUserInfo], summary="管理员列表")
def list_admin_users(
    db: Session = Depends(database.get_db),
):
    return db.query(models.AdminUser).order_by(models.AdminUser.id.asc()).all()


@router.put("/admin-users/{admin_id}/roles", response_model=dict, summary="分配管理员角色")
def set_admin_roles(
    admin_id: int,
    body: schemas.AdminRoleBindingUpdate,
    db: Session = Depends(database.get_db),
):
    admin = db.query(models.AdminUser).filter(models.AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    db.query(models.AdminUserRole).filter(models.AdminUserRole.admin_id == admin_id).delete()
    for role_id in body.role_ids:
        role = db.query(models.Role).filter(models.Role.id == role_id).first()
        if role:
            db.add(models.AdminUserRole(admin_id=admin_id, role_id=role_id))
    db.commit()
    return {"message": "管理员角色已更新"}


@router.get("/me/menus", response_model=list[str], summary="当前管理员菜单权限")
def get_me_menus(
    admin_id: int,
    db: Session = Depends(database.get_db),
):
    bindings = db.query(models.AdminUserRole).filter(models.AdminUserRole.admin_id == admin_id).all()
    if not bindings:
        return []
    role_ids = [x.role_id for x in bindings]
    codes = db.query(models.Permission.code).join(
        models.RolePermission,
        models.RolePermission.permission_id == models.Permission.id,
    ).filter(models.RolePermission.role_id.in_(role_ids)).all()
    return sorted({c[0] for c in codes})
