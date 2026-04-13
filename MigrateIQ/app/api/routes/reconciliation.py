from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.schemas import ReconciliationRequest, ReconciliationRunOut
from app.models.models import ReconciliationRun, DataObject
from app.services.reconciliation_service import create_reconciliation_run, generate_reconciliation_sql

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.post("/run", response_model=ReconciliationRunOut)
def trigger_reconciliation(payload: ReconciliationRequest, db: Session = Depends(get_db)):
    try:
        run = create_reconciliation_run(
            db,
            data_object_id=payload.data_object_id,
            view_id=payload.view_id,
            custom_sql=payload.custom_sql,
        )
        return run
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/generate-sql/{object_id}")
def get_generated_sql(object_id: int, db: Session = Depends(get_db)):
    obj = db.query(DataObject).filter(DataObject.id == object_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Data object not found")
    queries = generate_reconciliation_sql(obj)
    return {"object_id": object_id, "queries": queries}


@router.get("/runs/{object_id}", response_model=List[ReconciliationRunOut])
def list_runs(object_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ReconciliationRun)
        .filter(ReconciliationRun.data_object_id == object_id)
        .order_by(ReconciliationRun.created_at.desc())
        .all()
    )


@router.get("/runs/detail/{run_id}", response_model=ReconciliationRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(ReconciliationRun).filter(ReconciliationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
