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


def get_int_param(db, key: str, default: int) -> int:
    item = db.query(models.SystemParam).filter(models.SystemParam.key == key).first()
    if not item:
        return default
    try:
        return int(item.value)
    except ValueError:
        return default


def create_notification_log(db, reservation, type_, title, content):
    db.add(models.NotificationLog(
        student_id=reservation.student_id,
        reservation_id=reservation.id,
        type=type_,
        channel="in_app",
        title=title,
        content=content,
        status=models.NotificationStatus.sent,
    ))


def auto_cancel_overdue():
    """超时15分钟未签到的预约自动取消并记录违约"""
    db = SessionLocal()
    try:
        timeout_minutes = get_int_param(db, "CHECKIN_TIMEOUT_MINUTES", 15)
        cutoff = datetime.now() - timedelta(minutes=timeout_minutes)
        overdue = db.query(models.Reservation).filter(
            models.Reservation.status == "pending",
            models.Reservation.start_time <= cutoff,
        ).all()

        for r in overdue:
            r.status = models.ReservationStatus.violated
            violation = models.Violation(student_id=r.student_id, reservation_id=r.id)
            db.add(violation)
            create_notification_log(
                db,
                r,
                models.NotificationType.auto_cancel,
                "预约已自动取消",
                f"预约 #{r.id} 已因超时未签到自动取消，并记录违约。",
            )

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


def remind_before_start():
    """开始前提醒"""
    db = SessionLocal()
    try:
        before_minutes = get_int_param(db, "REMIND_BEFORE_MINUTES", 15)
        now = datetime.now()
        target = now + timedelta(minutes=before_minutes)
        window_start = target - timedelta(minutes=2)
        window_end = target + timedelta(minutes=1)
        reservations = db.query(models.Reservation).filter(
            models.Reservation.status == "pending",
            models.Reservation.start_time >= window_start,
            models.Reservation.start_time < window_end,
        ).all()
        for r in reservations:
            exists = db.query(models.NotificationLog).filter(
                models.NotificationLog.reservation_id == r.id,
                models.NotificationLog.type == models.NotificationType.before_start,
                models.NotificationLog.created_at >= now - timedelta(minutes=before_minutes + 2),
            ).first()
            if not exists:
                create_notification_log(
                    db,
                    r,
                    models.NotificationType.before_start,
                    "预约即将开始",
                    f"你的预约 #{r.id} 将在约 {before_minutes} 分钟后开始，请及时前往签到。",
                )
        if reservations:
            db.commit()
            print(f"[定时任务] 已发送开始前提醒 {len(reservations)} 条")
    finally:
        db.close()


def remind_after_start_uncheckin():
    """开始后未签到提醒"""
    db = SessionLocal()
    try:
        after_minutes = get_int_param(db, "REMIND_AFTER_START_MINUTES", 10)
        now = datetime.now()
        target = now - timedelta(minutes=after_minutes)
        window_start = target - timedelta(minutes=2)
        window_end = target + timedelta(minutes=1)
        reservations = db.query(models.Reservation).filter(
            models.Reservation.status == "pending",
            models.Reservation.start_time >= window_start,
            models.Reservation.start_time < window_end,
        ).all()
        for r in reservations:
            exists = db.query(models.NotificationLog).filter(
                models.NotificationLog.reservation_id == r.id,
                models.NotificationLog.type == models.NotificationType.after_start,
            ).first()
            if not exists:
                create_notification_log(
                    db,
                    r,
                    models.NotificationType.after_start,
                    "预约仍未签到",
                    f"你的预约 #{r.id} 已开始约 {after_minutes} 分钟，仍未签到，请尽快处理。",
                )
        if reservations:
            db.commit()
            print(f"[定时任务] 已发送未签到提醒 {len(reservations)} 条")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(auto_cancel_overdue, "interval", minutes=1, id="auto_cancel")
    scheduler.add_job(refresh_checkin_codes, "cron", hour=0, minute=0, id="refresh_codes")
    scheduler.add_job(remind_before_start, "interval", minutes=1, id="before_start_remind")
    scheduler.add_job(remind_after_start_uncheckin, "interval", minutes=1, id="after_start_remind")
    scheduler.start()
    # 启动时立即刷新一次签到码
    refresh_checkin_codes()
    return scheduler
