from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import database
import models

router = APIRouter(prefix="/stats", tags=["统计"])


@router.get("/occupancy", response_model=list[dict], summary="自习室座位占用率")
def occupancy_stats(
    room_id: int | None = Query(None),
    db: Session = Depends(database.get_db),
):
    rooms_query = db.query(models.Room).filter(models.Room.is_active == 1)
    if room_id:
        rooms_query = rooms_query.filter(models.Room.id == room_id)
    rooms = rooms_query.all()
    now = datetime.now()
    result = []
    for room in rooms:
        total = db.query(models.Seat).filter(
            models.Seat.room_id == room.id,
            models.Seat.is_active == 1,
        ).count()
        occupied = db.query(models.Reservation).join(
            models.Seat, models.Seat.id == models.Reservation.seat_id
        ).filter(
            models.Seat.room_id == room.id,
            models.Reservation.status.in_(["pending", "checked_in"]),
            models.Reservation.start_time <= now,
            models.Reservation.end_time > now,
        ).count()
        rate = round((occupied / total) * 100, 2) if total else 0
        result.append({
            "room_id": room.id,
            "room_name": room.name,
            "total_seats": total,
            "occupied_seats": occupied,
            "occupancy_rate": rate,
        })
    return result


@router.get("/reservations/trend", response_model=list[dict], summary="近期预约趋势")
def reservation_trend(
    days: int = Query(7, ge=1, le=60),
    db: Session = Depends(database.get_db),
):
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)
    output = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        start_dt = datetime(d.year, d.month, d.day, 0, 0, 0)
        end_dt = start_dt + timedelta(days=1)
        count = db.query(models.Reservation).filter(
            models.Reservation.created_at >= start_dt,
            models.Reservation.created_at < end_dt,
        ).count()
        output.append({"date": d.isoformat(), "reservation_count": count})
    return output
