from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from app.models.models import WaveStatus, ObjectStatus, DefectStatus, DefectSeverity, StageType


# ─── Wave ─────────────────────────────────────────────────────────────────────

class WaveBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: WaveStatus = WaveStatus.PLANNED
    target_go_live: Optional[datetime] = None


class WaveCreate(WaveBase):
    pass


class WaveUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WaveStatus] = None
    target_go_live: Optional[datetime] = None


class WaveOut(WaveBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── ObjectView ───────────────────────────────────────────────────────────────

class ObjectViewBase(BaseModel):
    view_name: str
    composite_key_fields: Optional[List[str]] = None
    extraction_table: Optional[str] = None
    transformation_table: Optional[str] = None
    invalid_table: Optional[str] = None
    enriched_table: Optional[str] = None
    loaded_table: Optional[str] = None


class ObjectViewCreate(ObjectViewBase):
    pass


class ObjectViewUpdate(BaseModel):
    view_name: Optional[str] = None
    composite_key_fields: Optional[List[str]] = None
    extraction_table: Optional[str] = None
    transformation_table: Optional[str] = None
    invalid_table: Optional[str] = None
    enriched_table: Optional[str] = None
    loaded_table: Optional[str] = None


class ObjectViewOut(ObjectViewBase):
    id: int
    extraction_count: int = 0
    transformation_count: int = 0
    invalid_count: int = 0
    enriched_count: int = 0
    loaded_count: int = 0
    extraction_duration: Optional[float] = None
    transformation_duration: Optional[float] = None
    loading_duration: Optional[float] = None
    last_refreshed: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── DataObject ───────────────────────────────────────────────────────────────

class DataObjectBase(BaseModel):
    name: str
    sap_object_code: Optional[str] = None
    description: Optional[str] = None
    composite_key_fields: Optional[List[str]] = None


class DataObjectCreate(DataObjectBase):
    wave_id: int
    views: Optional[List[ObjectViewCreate]] = []


class DataObjectUpdate(BaseModel):
    name: Optional[str] = None
    sap_object_code: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ObjectStatus] = None
    composite_key_fields: Optional[List[str]] = None


class DataObjectOut(DataObjectBase):
    id: int
    wave_id: int
    status: ObjectStatus
    total_extracted: int = 0
    total_transformed: int = 0
    total_invalid: int = 0
    total_enriched: int = 0
    total_loaded: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    views: List[ObjectViewOut] = []

    class Config:
        from_attributes = True


# ─── Reconciliation ───────────────────────────────────────────────────────────

class ReconciliationRequest(BaseModel):
    data_object_id: int
    view_id: Optional[int] = None
    custom_sql: Optional[str] = None


class ReconciliationRunOut(BaseModel):
    id: int
    data_object_id: int
    run_type: str
    sql_query: Optional[str]
    result_json: Optional[Any]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Defect ───────────────────────────────────────────────────────────────────

class DefectCreate(BaseModel):
    data_object_id: int
    title: str
    description: Optional[str] = None
    severity: DefectSeverity = DefectSeverity.MEDIUM
    source_stage: StageType = StageType.INVALID
    affected_keys: Optional[List[str]] = None
    assignee: Optional[str] = None


class DefectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[DefectSeverity] = None
    status: Optional[DefectStatus] = None
    assignee: Optional[str] = None
    resolution_notes: Optional[str] = None


class DefectOut(BaseModel):
    id: int
    data_object_id: int
    defect_id: str
    title: str
    description: Optional[str]
    severity: DefectSeverity
    status: DefectStatus
    source_stage: StageType
    affected_keys: Optional[List[str]]
    assignee: Optional[str]
    auto_generated: bool
    resolution_notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Dashboard Summary ────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_objects: int
    completed: int
    in_progress: int
    failed: int
    not_started: int
    blocked: int
    total_waves: int
    open_defects: int
    critical_defects: int
    overall_completion_pct: float
