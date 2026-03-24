from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date
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

router = APIRouter(prefix="/seats", tags=["座位"])


@router.get("/search", response_model=List[schemas.SeatDetail], summary="搜索可用座位")
def search_seats(
    date_str: str = Query(..., alias="date", description="日期，格式 YYYY-MM-DD"),
    start_time: str = Query(..., description="开始时间，格式 HH:MM 或 HH:MM:SS"),
    end_time: str = Query(..., description="结束时间，格式 HH:MM 或 HH:MM:SS"),
    has_power: Optional[int] = Query(None, description="是否需要插座 1/0"),
    by_window: Optional[int] = Query(None, description="是否需要靠窗 1/0"),
    room_id: Optional[int] = Query(None, description="指定自习室ID"),
    db: Session = Depends(database.get_db),
    current: Optional[models.Student] = Depends(get_optional_student),
):
    try:
        target_date = date.fromisoformat(date_str)
        sh = int(start_time.split(":")[0])
        eh = int(end_time.split(":")[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="日期或时间格式错误")

    start_dt = datetime(target_date.year, target_date.month, target_date.day, sh)
    end_dt = datetime(target_date.year, target_date.month, target_date.day, eh)

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")

    # 查询符合属性条件的座位
    seat_query = (
        db.query(models.Seat)
        .join(models.Room)
        .options(joinedload(models.Seat.room))
        .filter(models.Seat.is_active == 1, models.Room.is_active == 1)
    )

    # 院系过滤（未登录时只看全校通用）
    if current and current.department:
        seat_query = seat_query.filter(
            (models.Room.department == None) | (models.Room.department == current.department)
        )
    else:
        seat_query = seat_query.filter(models.Room.department == None)

    if has_power is not None:
        seat_query = seat_query.filter(models.Seat.has_power == has_power)
    if by_window is not None:
        seat_query = seat_query.filter(models.Seat.by_window == by_window)
    if room_id is not None:
        seat_query = seat_query.filter(models.Seat.room_id == room_id)

    all_seats = seat_query.all()

    # 排除在该时间段内已有有效预约的座位
    conflicting_seat_ids = (
        db.query(models.Reservation.seat_id)
        .filter(
            models.Reservation.status.in_(["pending", "checked_in"]),
            models.Reservation.start_time < end_dt,
            models.Reservation.end_time > start_dt,
        )
        .subquery()
    )

    available = [s for s in all_seats if s.id not in [r.seat_id for r in db.query(models.Reservation.seat_id).filter(
        models.Reservation.status.in_(["pending", "checked_in"]),
        models.Reservation.start_time < end_dt,
        models.Reservation.end_time > start_dt,
    ).all()]]

    return available


@router.post("/admin/{room_id}", response_model=schemas.SeatInfo, summary="管理员新增座位")
def admin_create_seat(room_id: int, body: schemas.SeatCreate, db: Session = Depends(database.get_db)):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="自习室不存在")
    existing = db.query(models.Seat).filter(
        models.Seat.room_id == room_id, models.Seat.seat_no == body.seat_no
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该座位编号已存在")
    seat = models.Seat(room_id=room_id, **body.model_dump())
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return seat


@router.put("/admin/{seat_id}", response_model=schemas.SeatInfo, summary="管理员更新座位属性")
def admin_update_seat(
    seat_id: int,
    has_power: Optional[int] = None,
    by_window: Optional[int] = None,
    is_active: Optional[int] = None,
    db: Session = Depends(database.get_db),
):
    seat = db.query(models.Seat).filter(models.Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="座位不存在")
    if has_power is not None:
        seat.has_power = has_power
    if by_window is not None:
        seat.by_window = by_window
    if is_active is not None:
        seat.is_active = is_active
    db.commit()
    db.refresh(seat)
    return seat
