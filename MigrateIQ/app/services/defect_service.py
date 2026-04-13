"""
Auto-generate defects from invalid table counts and manage defect lifecycle.
"""
from sqlalchemy.orm import Session
from app.models.models import Defect, DataObject, ObjectView, DefectSeverity, StageType
from datetime import datetime


def _next_defect_id(db: Session) -> str:
    count = db.query(Defect).count()
    return f"DEF-{(count + 1):04d}"


def auto_generate_defects(db: Session, data_object_id: int) -> list:
    """
    Inspect the invalid counts for each view and create defects
    if thresholds are exceeded. Returns list of new Defect objects.
    """
    obj = db.query(DataObject).filter(DataObject.id == data_object_id).first()
    if not obj:
        return []

    new_defects = []
    for view in obj.views:
        if view.invalid_count and view.invalid_count > 0:
            severity = (
                DefectSeverity.CRITICAL if view.invalid_count > 1000
                else DefectSeverity.HIGH if view.invalid_count > 100
                else DefectSeverity.MEDIUM
            )
            defect = Defect(
                data_object_id=data_object_id,
                defect_id=_next_defect_id(db),
                title=f"[AUTO] {view.invalid_count} invalid records in {view.view_name}",
                description=(
                    f"Automatically generated defect for view '{view.view_name}'. "
                    f"Invalid table: {view.invalid_table or 'N/A'}. "
                    f"Record count: {view.invalid_count}."
                ),
                severity=severity,
                source_stage=StageType.INVALID,
                auto_generated=True,
            )
            db.add(defect)
            db.flush()
            new_defects.append(defect)

    db.commit()
    return new_defects
