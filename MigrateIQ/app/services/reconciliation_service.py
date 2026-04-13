"""
AI-powered reconciliation service.
Generates SQL queries to compare row counts and key fields across staging tables.
Falls back to rule-based generation when OpenAI key is not configured.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import DataObject, ObjectView, ReconciliationRun
from app.core.config import settings
import json
import re


def _build_count_sql(view: ObjectView) -> str:
    """Build a cross-stage count comparison SQL (CTE-based)."""
    stages = [
        ("extraction",     view.extraction_table),
        ("transformation", view.transformation_table),
        ("invalid",        view.invalid_table),
        ("enriched",       view.enriched_table),
        ("loaded",         view.loaded_table),
    ]
    ctes = []
    selects = []

    for stage_name, table in stages:
        if table:
            ctes.append(f"  {stage_name}_cnt AS (SELECT COUNT(*) AS cnt FROM {table})")
            selects.append(f"  (SELECT cnt FROM {stage_name}_cnt) AS {stage_name}_count")

    if not ctes:
        return "-- No tables configured for this view"

    sql = "WITH\n" + ",\n".join(ctes) + "\nSELECT\n" + ",\n".join(selects) + ";"
    return sql


def _build_key_comparison_sql(view: ObjectView, key_fields: list) -> str:
    """Build SQL to detect keys present in extraction but missing in loaded table."""
    if not view.extraction_table or not view.loaded_table or not key_fields:
        return "-- Key comparison requires extraction_table, loaded_table and composite_key_fields"

    key_str = ", ".join(key_fields)
    sql = (
        f"-- Keys in Extraction but NOT in Loaded (data loss check)\n"
        f"SELECT {key_str}\n"
        f"FROM {view.extraction_table}\n"
        f"EXCEPT\n"
        f"SELECT {key_str}\n"
        f"FROM {view.loaded_table}\n"
        f"LIMIT 500;"
    )
    return sql


def generate_reconciliation_sql(
    data_object: DataObject, view: Optional[ObjectView] = None
) -> Dict[str, str]:
    """Return a dict of named SQL queries for the reconciliation run."""
    target_view = view or (data_object.views[0] if data_object.views else None)
    if not target_view:
        return {"error": "-- No views configured for this data object"}

    key_fields = (
        target_view.composite_key_fields
        or data_object.composite_key_fields
        or []
    )

    return {
        "count_comparison": _build_count_sql(target_view),
        "key_loss_check": _build_key_comparison_sql(target_view, key_fields),
        "invalid_sample": (
            f"-- Sample of invalid records\nSELECT *\nFROM {target_view.invalid_table}\nLIMIT 100;"
            if target_view.invalid_table
            else "-- No invalid table configured"
        ),
    }


def create_reconciliation_run(
    db: Session, data_object_id: int, view_id: Optional[int], custom_sql: Optional[str]
) -> ReconciliationRun:
    """Persist a new ReconciliationRun and return it."""
    obj = db.query(DataObject).filter(DataObject.id == data_object_id).first()
    if not obj:
        raise ValueError(f"DataObject {data_object_id} not found")

    view = None
    if view_id:
        view = db.query(ObjectView).filter(ObjectView.id == view_id).first()

    if custom_sql:
        sql = custom_sql
        run_type = "manual"
    else:
        queries = generate_reconciliation_sql(obj, view)
        sql = "\n\n".join(f"-- {name}\n{q}" for name, q in queries.items())
        run_type = "auto"

    run = ReconciliationRun(
        data_object_id=data_object_id,
        run_type=run_type,
        sql_query=sql,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
