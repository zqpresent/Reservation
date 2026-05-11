from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import database
import models
import schemas

router = APIRouter(prefix="/system", tags=["系统参数"])


@router.get("/params", response_model=list[schemas.SystemParamInfo], summary="查询系统参数")
def get_system_params(
    db: Session = Depends(database.get_db),
):
    return db.query(models.SystemParam).order_by(models.SystemParam.key.asc()).all()


@router.put("/params/{key}", response_model=schemas.SystemParamInfo, summary="更新单个系统参数")
def update_system_param(
    key: str,
    body: schemas.SystemParamUpdate,
    db: Session = Depends(database.get_db),
):
    item = db.query(models.SystemParam).filter(models.SystemParam.key == key).first()
    if not item:
        raise HTTPException(status_code=404, detail="参数不存在")
    item.value = body.value
    db.commit()
    db.refresh(item)
    return item


@router.put("/params", response_model=list[schemas.SystemParamInfo], summary="批量更新系统参数")
def batch_update_params(
    body: schemas.SystemParamBatchUpdate,
    db: Session = Depends(database.get_db),
):
    updated = []
    for entry in body.items:
        item = db.query(models.SystemParam).filter(models.SystemParam.key == entry.key).first()
        if not item:
            item = models.SystemParam(key=entry.key, value=entry.value, description="")
            db.add(item)
            db.flush()
        else:
            item.value = entry.value
        updated.append(item)
    db.commit()
    return updated
