from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Defect, DefectStatus
from app.schemas.schemas import DefectCreate, DefectUpdate, DefectOut
from app.services.defect_service import auto_generate_defects, _next_defect_id

router = APIRouter(prefix="/defects", tags=["Defects"])


@router.get("/", response_model=List[DefectOut])
def list_defects(
    object_id: Optional[int] = None,
    status: Optional[DefectStatus] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Defect)
    if object_id:
        q = q.filter(Defect.data_object_id == object_id)
    if status:
        q = q.filter(Defect.status == status)
    return q.order_by(Defect.created_at.desc()).all()


@router.post("/", response_model=DefectOut, status_code=status.HTTP_201_CREATED)
def create_defect(payload: DefectCreate, db: Session = Depends(get_db)):
    defect = Defect(
        defect_id=_next_defect_id(db),
        **payload.model_dump()
    )
    db.add(defect)
    db.commit()
    db.refresh(defect)
    return defect


@router.post("/auto-generate/{object_id}", response_model=List[DefectOut])
def auto_generate(object_id: int, db: Session = Depends(get_db)):
    new_defects = auto_generate_defects(db, object_id)
    if not new_defects:
        return []
    return new_defects


@router.get("/{defect_id}", response_model=DefectOut)
def get_defect(defect_id: int, db: Session = Depends(get_db)):
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    return defect


@router.patch("/{defect_id}", response_model=DefectOut)
def update_defect(defect_id: int, payload: DefectUpdate, db: Session = Depends(get_db)):
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(defect, key, val)
    db.commit()
    db.refresh(defect)
    return defect


@router.delete("/{defect_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_defect(defect_id: int, db: Session = Depends(get_db)):
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    db.delete(defect)
    db.commit()
