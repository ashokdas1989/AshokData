from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Enum as SAEnum, JSON, Float, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class WaveStatus(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class ObjectStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class StageType(str, enum.Enum):
    EXTRACTION = "extraction"
    TRANSFORMATION = "transformation"
    INVALID = "invalid"
    ENRICHED = "enriched"
    LOADED = "loaded"


class DefectStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    CLOSED = "closed"
    WONT_FIX = "wont_fix"


class DefectSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ─── Migration Wave ──────────────────────────────────────────────────────────

class MigrationWave(Base):
    __tablename__ = "migration_waves"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    status = Column(SAEnum(WaveStatus), default=WaveStatus.PLANNED)
    target_go_live = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    data_objects = relationship("DataObject", back_populates="wave", cascade="all, delete-orphan")


# ─── Data Object ─────────────────────────────────────────────────────────────

class DataObject(Base):
    __tablename__ = "data_objects"

    id = Column(Integer, primary_key=True, index=True)
    wave_id = Column(Integer, ForeignKey("migration_waves.id"), nullable=False)
    name = Column(String(200), nullable=False)           # e.g. "Material Master"
    sap_object_code = Column(String(50))                 # e.g. "MM01"
    description = Column(Text)
    status = Column(SAEnum(ObjectStatus), default=ObjectStatus.NOT_STARTED)
    composite_key_fields = Column(JSON)                  # ["MATNR", "MANDT"]
    total_extracted = Column(Integer, default=0)
    total_transformed = Column(Integer, default=0)
    total_invalid = Column(Integer, default=0)
    total_enriched = Column(Integer, default=0)
    total_loaded = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    wave = relationship("MigrationWave", back_populates="data_objects")
    views = relationship("ObjectView", back_populates="data_object", cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="data_object", cascade="all, delete-orphan")
    reconciliation_runs = relationship("ReconciliationRun", back_populates="data_object", cascade="all, delete-orphan")


# ─── Object View (e.g. Basic View, Purchasing View) ──────────────────────────

class ObjectView(Base):
    __tablename__ = "object_views"

    id = Column(Integer, primary_key=True, index=True)
    data_object_id = Column(Integer, ForeignKey("data_objects.id"), nullable=False)
    view_name = Column(String(100), nullable=False)      # "Basic Data", "Purchasing"
    composite_key_fields = Column(JSON)                  # override keys per view

    # Stage table / path config
    extraction_table = Column(String(300))
    transformation_table = Column(String(300))
    invalid_table = Column(String(300))
    enriched_table = Column(String(300))
    loaded_table = Column(String(300))

    # Row counts per stage
    extraction_count = Column(Integer, default=0)
    transformation_count = Column(Integer, default=0)
    invalid_count = Column(Integer, default=0)
    enriched_count = Column(Integer, default=0)
    loaded_count = Column(Integer, default=0)

    # Timing metrics (seconds)
    extraction_duration = Column(Float)
    transformation_duration = Column(Float)
    loading_duration = Column(Float)

    last_refreshed = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    data_object = relationship("DataObject", back_populates="views")
    stage_audits = relationship("StageAudit", back_populates="view", cascade="all, delete-orphan")


# ─── Stage Audit (history of count snapshots) ────────────────────────────────

class StageAudit(Base):
    __tablename__ = "stage_audits"

    id = Column(Integer, primary_key=True, index=True)
    view_id = Column(Integer, ForeignKey("object_views.id"), nullable=False)
    stage = Column(SAEnum(StageType))
    row_count = Column(Integer)
    duration_seconds = Column(Float)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())

    view = relationship("ObjectView", back_populates="stage_audits")


# ─── Reconciliation Run ───────────────────────────────────────────────────────

class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id = Column(Integer, primary_key=True, index=True)
    data_object_id = Column(Integer, ForeignKey("data_objects.id"), nullable=False)
    run_type = Column(String(50))          # "auto" | "manual"
    sql_query = Column(Text)
    result_json = Column(JSON)
    status = Column(String(30), default="pending")  # pending | running | success | error
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    data_object = relationship("DataObject", back_populates="reconciliation_runs")


# ─── Defect ───────────────────────────────────────────────────────────────────

class Defect(Base):
    __tablename__ = "defects"

    id = Column(Integer, primary_key=True, index=True)
    data_object_id = Column(Integer, ForeignKey("data_objects.id"), nullable=False)
    defect_id = Column(String(30), unique=True)          # "DEF-0001"
    title = Column(String(300), nullable=False)
    description = Column(Text)
    severity = Column(SAEnum(DefectSeverity), default=DefectSeverity.MEDIUM)
    status = Column(SAEnum(DefectStatus), default=DefectStatus.OPEN)
    source_stage = Column(SAEnum(StageType), default=StageType.INVALID)
    affected_keys = Column(JSON)
    assignee = Column(String(100))
    auto_generated = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    data_object = relationship("DataObject", back_populates="defects")
