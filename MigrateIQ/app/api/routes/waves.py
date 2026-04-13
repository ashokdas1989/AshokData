from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import MigrationWave
from app.schemas.schemas import WaveCreate, WaveUpdate, WaveOut

router = APIRouter(prefix="/waves", tags=["Migration Waves"])


@router.get("/", response_model=List[WaveOut])
def list_waves(db: Session = Depends(get_db)):
    return db.query(MigrationWave).order_by(MigrationWave.created_at.desc()).all()


@router.post("/", response_model=WaveOut, status_code=status.HTTP_201_CREATED)
def create_wave(payload: WaveCreate, db: Session = Depends(get_db)):
    wave = MigrationWave(**payload.model_dump())
    db.add(wave)
    db.commit()
    db.refresh(wave)
    return wave


@router.get("/{wave_id}", response_model=WaveOut)
def get_wave(wave_id: int, db: Session = Depends(get_db)):
    wave = db.query(MigrationWave).filter(MigrationWave.id == wave_id).first()
    if not wave:
        raise HTTPException(status_code=404, detail="Wave not found")
    return wave


@router.patch("/{wave_id}", response_model=WaveOut)
def update_wave(wave_id: int, payload: WaveUpdate, db: Session = Depends(get_db)):
    wave = db.query(MigrationWave).filter(MigrationWave.id == wave_id).first()
    if not wave:
        raise HTTPException(status_code=404, detail="Wave not found")
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(wave, key, val)
    db.commit()
    db.refresh(wave)
    return wave


@router.delete("/{wave_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wave(wave_id: int, db: Session = Depends(get_db)):
    wave = db.query(MigrationWave).filter(MigrationWave.id == wave_id).first()
    if not wave:
        raise HTTPException(status_code=404, detail="Wave not found")
    db.delete(wave)
    db.commit()
