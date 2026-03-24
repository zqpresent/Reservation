from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta, date as date_type
import database
import models
import schemas
import auth as auth_utils
import os

router = APIRouter(prefix="/reservations", tags=["预约"])

MAX_HOURS = int(os.getenv("MAX_RESERVE_HOURS", "4"))


def reservation_to_dict(r: models.Reservation) -> dict:
    return {
        "id": r.id,
        "student_id": r.student_id,
        "seat_id": r.seat_id,
        "start_time": r.start_time.isoformat(),
        "end_time": r.end_time.isoformat(),
        "status": r.status.value if hasattr(r.status, 'value') else r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "date": r.start_time.strftime("%Y-%m-%d"),
        "room_name": r.seat.room.name if r.seat and r.seat.room else None,
        "seat_no": r.seat.seat_no if r.seat else None,
        "has_power": r.seat.has_power if r.seat else None,
        "by_window": r.seat.by_window if r.seat else None,
    }


@router.post("", summary="学生新增预约")
def create_reservation(
    body: schemas.ReservationCreate,
    db: Session = Depends(database.get_db),
):
    # 解析日期时间
    try:
        target_date = date_type.fromisoformat(body.date)
        sh = int(body.start_time.split(":")[0])
        eh = int(body.end_time.split(":")[0])
        start_dt = datetime(target_date.year, target_date.month, target_date.day, sh)
        end_dt = datetime(target_date.year, target_date.month, target_date.day, eh)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="日期或时间格式错误")

    # 时长校验
    duration = (end_dt - start_dt).total_seconds() / 3600
    if duration <= 0 or duration > MAX_HOURS:
        raise HTTPException(status_code=400, detail=f"预约时长需在 1 到 {MAX_HOURS} 小时之间")

    # 检查座位是否存在且可用
    seat = db.query(models.Seat).filter(models.Seat.id == body.seat_id, models.Seat.is_active == 1).first()
    if not seat:
        raise HTTPException(status_code=404, detail="座位不存在或已不可用")

    # 冲突检测
    conflict = db.query(models.Reservation).filter(
        models.Reservation.seat_id == body.seat_id,
        models.Reservation.status.in_(["pending", "checked_in"]),
        models.Reservation.start_time < end_dt,
        models.Reservation.end_time > start_dt,
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="该时间段座位已被预约")

    if not body.student_id:
        raise HTTPException(status_code=400, detail="请提供 student_id")
    reservation = models.Reservation(
        student_id=body.student_id,
        seat_id=body.seat_id,
        start_time=start_dt,
        end_time=end_dt,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    r = db.query(models.Reservation).options(
        joinedload(models.Reservation.seat).joinedload(models.Seat.room)
    ).filter(models.Reservation.id == reservation.id).first()
    return reservation_to_dict(r)


@router.get("", summary="查询我的预约")
def list_my_reservations(
    status: Optional[str] = Query(None),
    student_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
):
    query = (
        db.query(models.Reservation)
        .options(joinedload(models.Reservation.seat).joinedload(models.Seat.room))
    )
    if student_id:
        query = query.filter(models.Reservation.student_id == student_id)
    if status:
        query = query.filter(models.Reservation.status == status)
    return [reservation_to_dict(r) for r in query.order_by(models.Reservation.start_time.desc()).all()]


@router.delete("/{reservation_id}", response_model=schemas.MessageResponse, summary="学生取消预约")
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(database.get_db),
):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.id == reservation_id,
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="预约不存在")
    if reservation.status != "pending":
        raise HTTPException(status_code=400, detail="只有待签到的预约可以取消")
    reservation.status = models.ReservationStatus.cancelled
    db.commit()
    return {"message": "预约已取消"}


@router.post("/checkin", response_model=schemas.MessageResponse, summary="学生签到")
def check_in(
    body: schemas.CheckInRequest,
    db: Session = Depends(database.get_db),
):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.id == body.reservation_id,
        models.Reservation.status == "pending",
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="预约不存在或状态不正确")

    now = datetime.now()
    # 允许提前5分钟签到
    if now < reservation.start_time - timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="还未到签到时间")
    if now > reservation.start_time + timedelta(minutes=15):
        raise HTTPException(status_code=400, detail="签到已超时，预约即将自动取消")

    # 验证签到码
    seat = db.query(models.Seat).filter(models.Seat.id == reservation.seat_id).first()
    room = db.query(models.Room).filter(models.Room.id == seat.room_id).first()

    from datetime import date
    if room.code_updated_at != date.today() or room.checkin_code != body.checkin_code:
        raise HTTPException(status_code=400, detail="签到码错误")

    reservation.status = models.ReservationStatus.checked_in
    db.commit()
    return {"message": "签到成功"}


# -------------------------------------------------------
# 管理员接口
# -------------------------------------------------------
@router.get("/admin/all", summary="管理员查看所有预约")
def admin_list_reservations(
    status: Optional[str] = Query(None),
    student_id: Optional[int] = Query(None),
    room_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
):
    query = (
        db.query(models.Reservation)
        .options(joinedload(models.Reservation.seat).joinedload(models.Seat.room))
    )
    if status:
        query = query.filter(models.Reservation.status == status)
    if student_id:
        query = query.filter(models.Reservation.student_id == student_id)
    if room_id:
        query = query.join(models.Seat).filter(models.Seat.room_id == room_id)
    return [reservation_to_dict(r) for r in query.order_by(models.Reservation.start_time.desc()).all()]


@router.get("/admin/violations", response_model=List[dict], summary="管理员查看违约记录")
def admin_list_violations(
    db: Session = Depends(database.get_db),
):
    violations = db.query(models.Violation).options(
        joinedload(models.Violation.student),
        joinedload(models.Violation.reservation),
    ).order_by(models.Violation.violated_at.desc()).all()

    return [
        {
            "id": v.id,
            "student_id": v.student_id,
            "student_name": v.student.name,
            "student_no": v.student.student_no,
            "reservation_id": v.reservation_id,
            "violated_at": v.violated_at,
        }
        for v in violations
    ]
