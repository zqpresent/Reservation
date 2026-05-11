from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import database
import models

router = APIRouter(prefix="/notifications", tags=["通知"])


@router.get("/logs", response_model=List[dict], summary="查询通知发送记录")
def list_notification_logs(
    student_id: Optional[int] = Query(None),
    reservation_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(database.get_db),
):
    query = db.query(models.NotificationLog).order_by(models.NotificationLog.created_at.desc())
    if student_id:
        query = query.filter(models.NotificationLog.student_id == student_id)
    if reservation_id:
        query = query.filter(models.NotificationLog.reservation_id == reservation_id)
    if type:
        query = query.filter(models.NotificationLog.type == type)
    return [
        {
            "id": row.id,
            "student_id": row.student_id,
            "reservation_id": row.reservation_id,
            "type": row.type.value if hasattr(row.type, "value") else row.type,
            "channel": row.channel,
            "title": row.title,
            "content": row.content,
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "created_at": row.created_at,
        }
        for row in query.all()
    ]
