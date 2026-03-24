"""
定时任务模块
- 每分钟：检查超时未签到的预约，自动取消并记录违约
- 每天凌晨0点：刷新所有自习室的签到码
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, date
from database import SessionLocal
import models
import random
import string


def auto_cancel_overdue():
    """超时15分钟未签到的预约自动取消并记录违约"""
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(minutes=15)
        overdue = db.query(models.Reservation).filter(
            models.Reservation.status == "pending",
            models.Reservation.start_time <= cutoff,
        ).all()

        for r in overdue:
            r.status = models.ReservationStatus.violated
            violation = models.Violation(student_id=r.student_id, reservation_id=r.id)
            db.add(violation)

        if overdue:
            db.commit()
            print(f"[定时任务] 自动取消 {len(overdue)} 条超时预约")
    finally:
        db.close()


def refresh_checkin_codes():
    """每天刷新所有自习室的签到码"""
    db = SessionLocal()
    try:
        today = date.today()
        rooms = db.query(models.Room).filter(models.Room.is_active == 1).all()
        for room in rooms:
            if room.code_updated_at != today:
                room.checkin_code = ''.join(random.choices(string.digits, k=6))
                room.code_updated_at = today
        db.commit()
        print(f"[定时任务] 已刷新 {len(rooms)} 个自习室签到码")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(auto_cancel_overdue, "interval", minutes=1, id="auto_cancel")
    scheduler.add_job(refresh_checkin_codes, "cron", hour=0, minute=0, id="refresh_codes")
    scheduler.start()
    # 启动时立即刷新一次签到码
    refresh_checkin_codes()
    return scheduler
