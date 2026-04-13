from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from app.models.models import DataObject, ObjectView, MigrationWave
from app.schemas.schemas import (
    DataObjectCreate, DataObjectUpdate, DataObjectOut,
    ObjectViewCreate, ObjectViewUpdate, ObjectViewOut,
    DashboardSummary
)
from app.models.models import ObjectStatus

router = APIRouter(prefix="/objects", tags=["Data Objects"])


# ─── Dashboard summary ────────────────────────────────────────────────────────

@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    from app.models.models import Defect, DefectStatus, DefectSeverity

    all_objects = db.query(DataObject).all()
    total = len(all_objects)
    completed = sum(1 for o in all_objects if o.status == ObjectStatus.COMPLETED)
    in_progress = sum(1 for o in all_objects if o.status == ObjectStatus.IN_PROGRESS)
    failed = sum(1 for o in all_objects if o.status == ObjectStatus.FAILED)
    not_started = sum(1 for o in all_objects if o.status == ObjectStatus.NOT_STARTED)
    blocked = sum(1 for o in all_objects if o.status == ObjectStatus.BLOCKED)
    open_defects = db.query(Defect).filter(Defect.status == DefectStatus.OPEN).count()
    critical = db.query(Defect).filter(
        Defect.severity == DefectSeverity.CRITICAL,
        Defect.status == DefectStatus.OPEN
    ).count()
    waves = db.query(MigrationWave).count()
    pct = round((completed / total * 100) if total else 0, 1)

    return DashboardSummary(
        total_objects=total,
        completed=completed,
        in_progress=in_progress,
        failed=failed,
        not_started=not_started,
        blocked=blocked,
        total_waves=waves,
        open_defects=open_defects,
        critical_defects=critical,
        overall_completion_pct=pct,
    )


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[DataObjectOut])
def list_objects(
    wave_id: Optional[int] = None,
    status: Optional[ObjectStatus] = None,
    db: Session = Depends(get_db)
):
    q = db.query(DataObject).options(joinedload(DataObject.views))
    if wave_id:
        q = q.filter(DataObject.wave_id == wave_id)
    if status:
        q = q.filter(DataObject.status == status)
    return q.order_by(DataObject.created_at.desc()).all()


@router.post("/", response_model=DataObjectOut, status_code=status.HTTP_201_CREATED)
def create_object(payload: DataObjectCreate, db: Session = Depends(get_db)):
    wave = db.query(MigrationWave).filter(MigrationWave.id == payload.wave_id).first()
    if not wave:
        raise HTTPException(status_code=404, detail="Wave not found")

    views_data = payload.views or []
    obj_data = payload.model_dump(exclude={"views"})
    obj = DataObject(**obj_data)
    db.add(obj)
    db.flush()

    for v in views_data:
        view = ObjectView(data_object_id=obj.id, **v.model_dump())
        db.add(view)

    # If no views given, create a default one
    if not views_data:
        db.add(ObjectView(data_object_id=obj.id, view_name="Default View"))

    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{obj_id}", response_model=DataObjectOut)
def get_object(obj_id: int, db: Session = Depends(get_db)):
    obj = db.query(DataObject).options(joinedload(DataObject.views)).filter(DataObject.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Data object not found")
    return obj


@router.patch("/{obj_id}", response_model=DataObjectOut)
def update_object(obj_id: int, payload: DataObjectUpdate, db: Session = Depends(get_db)):
    obj = db.query(DataObject).filter(DataObject.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Data object not found")
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(obj, key, val)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(obj_id: int, db: Session = Depends(get_db)):
    obj = db.query(DataObject).filter(DataObject.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Data object not found")
    db.delete(obj)
    db.commit()


# ─── Views sub-resource ───────────────────────────────────────────────────────

@router.post("/{obj_id}/views", response_model=ObjectViewOut, status_code=status.HTTP_201_CREATED)
def add_view(obj_id: int, payload: ObjectViewCreate, db: Session = Depends(get_db)):
    obj = db.query(DataObject).filter(DataObject.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Data object not found")
    view = ObjectView(data_object_id=obj_id, **payload.model_dump())
    db.add(view)
    db.commit()
    db.refresh(view)
    return view


@router.patch("/{obj_id}/views/{view_id}", response_model=ObjectViewOut)
def update_view(obj_id: int, view_id: int, payload: ObjectViewUpdate, db: Session = Depends(get_db)):
    view = db.query(ObjectView).filter(
        ObjectView.id == view_id, ObjectView.data_object_id == obj_id
    ).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(view, key, val)
    db.commit()
    db.refresh(view)
    return view


@router.delete("/{obj_id}/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_view(obj_id: int, view_id: int, db: Session = Depends(get_db)):
    view = db.query(ObjectView).filter(
        ObjectView.id == view_id, ObjectView.data_object_id == obj_id
    ).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    db.delete(view)
    db.commit()
