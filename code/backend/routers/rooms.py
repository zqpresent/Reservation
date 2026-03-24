from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
import database
import models
import schemas
import auth as auth_utils

oauth2_optional = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_optional_student(
    token: Optional[str] = Depends(oauth2_optional),
    db: Session = Depends(database.get_db),
) -> Optional[models.Student]:
    if not token:
        return None
    try:
        payload = auth_utils.decode_token(token)
        if payload.get("type") != "student":
            return None
        return db.query(models.Student).filter(models.Student.id == payload.get("sub")).first()
    except Exception:
        return None

router = APIRouter(prefix="/rooms", tags=["自习室"])


@router.get("", response_model=List[schemas.RoomInfo], summary="查询可用自习室列表")
def list_rooms(
    db: Session = Depends(database.get_db),
    current: Optional[models.Student] = Depends(get_optional_student),
):
    """
    返回对当前学生可见的自习室：
    - 未登录或无院系：仅全校通用（department 为 NULL）
    - 已登录且有院系：全校通用 + 所在院系
    """
    query = db.query(models.Room).filter(models.Room.is_active == 1)
    if current and current.department:
        query = query.filter(
            (models.Room.department == None) | (models.Room.department == current.department)
        )
    else:
        query = query.filter(models.Room.department == None)
    return query.all()


@router.get("/{room_id}", response_model=schemas.RoomInfo, summary="查询单个自习室详情")
def get_room(
    room_id: int,
    db: Session = Depends(database.get_db),
):
    room = db.query(models.Room).filter(models.Room.id == room_id, models.Room.is_active == 1).first()
    if not room:
        raise HTTPException(status_code=404, detail="自习室不存在")
    return room


@router.get("/{room_id}/seats", response_model=List[schemas.SeatInfo], summary="查询教室内所有座位")
def list_seats(
    room_id: int,
    db: Session = Depends(database.get_db),
):
    room = db.query(models.Room).filter(models.Room.id == room_id, models.Room.is_active == 1).first()
    if not room:
        raise HTTPException(status_code=404, detail="自习室不存在")
    seats = db.query(models.Seat).filter(models.Seat.room_id == room_id, models.Seat.is_active == 1).all()
    return seats


# -------------------------------------------------------
# 管理员接口
# -------------------------------------------------------
@router.get("/admin/all", response_model=List[schemas.RoomInfo], summary="管理员查询所有自习室")
def admin_list_rooms(db: Session = Depends(database.get_db)):
    return db.query(models.Room).all()


@router.post("/admin", response_model=schemas.RoomInfo, summary="管理员新增自习室")
def admin_create_room(body: schemas.RoomCreate, db: Session = Depends(database.get_db)):
    room = models.Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/admin/{room_id}", response_model=schemas.RoomInfo, summary="管理员修改自习室")
def admin_update_room(room_id: int, body: schemas.RoomUpdate, db: Session = Depends(database.get_db)):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="自习室不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/admin/{room_id}", response_model=schemas.MessageResponse, summary="管理员注销自习室")
def admin_delete_room(room_id: int, db: Session = Depends(database.get_db)):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="自习室不存在")
    room.is_active = 0
    db.commit()
    return {"message": "自习室已注销"}
