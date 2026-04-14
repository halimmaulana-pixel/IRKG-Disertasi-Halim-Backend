from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import AcceptedMapping, KGNode
import services.pipeline_runner as pipeline_runner
import services.stage_data as stage_data

router = APIRouter()


class PipelineRunRequest(BaseModel):
    mode: str = "all"


class PipelineModeRequest(BaseModel):
    readonly: bool


@router.get("/mode")
def get_pipeline_mode():
    return pipeline_runner.get_runtime_mode()


@router.post("/mode")
def set_pipeline_mode(req: PipelineModeRequest):
    return pipeline_runner.set_runtime_mode(readonly=req.readonly)


@router.post("/run")
def run_pipeline(req: PipelineRunRequest):
    """
    Start pipeline async job.
    mode: "all", "pipeline_only", atau "refresh_db".
    """
    if req.mode not in {"all", "pipeline_only", "refresh_db"}:
        raise HTTPException(400, "mode harus 'all', 'pipeline_only', atau 'refresh_db'")
    return pipeline_runner.start_pipeline_job(mode=req.mode)


@router.get("/status/{job_id}")
def get_pipeline_status(job_id: str):
    data = pipeline_runner.get_job_status(job_id)
    if not data:
        raise HTTPException(404, "job tidak ditemukan")
    return data


@router.get("/stages/{job_id}")
def get_pipeline_stages(job_id: str):
    data = pipeline_runner.get_job_stages(job_id)
    if not data:
        raise HTTPException(404, "job tidak ditemukan")
    return data


@router.get("/stage-output/{job_id}/{stage_id}")
def get_stage_output(job_id: str, stage_id: str):
    data = pipeline_runner.get_stage_output_preview(job_id, stage_id)
    if not data:
        raise HTTPException(404, "job tidak ditemukan")
    return data


@router.get("/stream/{job_id}")
def stream_pipeline_events(job_id: str):
    return StreamingResponse(
        pipeline_runner.sse_event_stream(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/trace/{source_id}")
def get_pipeline_trace(
    source_id: str,
    task: str = Query("T1a"),
    config: str = Query("v1.2"),
    db: Session = Depends(get_db)
):
    """Ambil data untuk pipeline trace visualization."""
    accepted = db.query(AcceptedMapping).filter(
        AcceptedMapping.source_id == source_id,
        AcceptedMapping.task == task,
        AcceptedMapping.config == config,
    ).order_by(AcceptedMapping.s_final.desc()).limit(20).all()

    candidates = []
    for m in accepted:
        node = db.query(KGNode).filter(KGNode.id == m.target_id).first()
        candidates.append({
            "target_id": m.target_id,
            "target_label": m.target_label,
            "target_type": m.target_type,
            "target_description": node.description[:200] if node and node.description else "",
            "s_sem": round(m.s_sem, 4),
            "s_gr": round(m.s_gr, 4),
            "s_con": round(m.s_con, 4),
            "s_final": round(m.s_final, 4),
            "forced_top1": m.forced_top1,
            "rank": 0,
        })

    candidates.sort(key=lambda x: x["s_final"], reverse=True)
    for i, c in enumerate(candidates):
        c["rank"] = i + 1

    config_weights = {
        "v0.9": {"alpha": 1.00, "beta": 0.00, "gamma": 0.00},
        "v1.0": {"alpha": 0.60, "beta": 0.25, "gamma": 0.15},
        "v1.1": {"alpha": 0.60, "beta": 0.25, "gamma": 0.15},
        "v1.2": {"alpha": 0.34, "beta": 0.33, "gamma": 0.33},
        "v1.3": {"alpha": 0.60, "beta": 0.25, "gamma": 0.15},
        "v1.4": {"alpha": 0.55, "beta": 0.30, "gamma": 0.15},
    }
    weights = config_weights.get(config, config_weights["v1.2"])

    return {
        "source_id": source_id,
        "task": task,
        "config": config,
        "weights": weights,
        "n_accepted": sum(1 for c in candidates if not c["forced_top1"]),
        "n_forced": sum(1 for c in candidates if c["forced_top1"]),
        "candidates": candidates,
        "steps": [
            {"step": 1, "name": "Input CPL", "description": "Translate via bridge dictionary (ID -> EN terms)"},
            {"step": 2, "name": "TF-IDF Vectorization", "description": "Cosine similarity vs target corpus"},
            {"step": 3, "name": "Top-k Candidates", "description": "Select top semantic candidates"},
            {"step": 4, "name": "Graph Cohesion (S_gr)", "description": "Induced subgraph density in ESCO relation graph"},
            {"step": 5, "name": "Hybrid Scoring", "description": f"S_final = {weights['alpha']}*S_sem + {weights['beta']}*S_gr + {weights['gamma']}*S_con"},
            {"step": 6, "name": "Acceptance Gate", "description": f"tau = median S_final (config {config}). Accepted if S_final >= tau"},
        ]
    }


@router.get("/latest")
def get_latest_job():
    """Return status + stages dari job pipeline terakhir yang dijalankan."""
    job_id = pipeline_runner.get_latest_job_id()
    if not job_id:
        return {"job_id": None, "status": None, "stages": []}
    status = pipeline_runner.get_job_status(job_id)
    stages = pipeline_runner.get_job_stages(job_id)
    return {
        "job_id": job_id,
        "status": status,
        "stages": stages.get("stages", []) if stages else [],
    }


@router.get("/stage-data/{stage_id}")
def get_stage_visualized_data(stage_id: str):
    """Return rich, visualizable output data for a specific pipeline stage."""
    return stage_data.get_stage_data(stage_id)


@router.get("/tasks")
def get_available_tasks():
    return [
        {"id": "T1a", "name": "CPL-SI -> ESCO Skills", "prodi": "SI", "target": "ESCO"},
        {"id": "T1b", "name": "CPL-TI -> ESCO Skills", "prodi": "TI", "target": "ESCO"},
        {"id": "T2a", "name": "CPL-SI -> O*NET", "prodi": "SI", "target": "ONET"},
        {"id": "T2b", "name": "CPL-TI -> O*NET", "prodi": "TI", "target": "ONET"},
        {"id": "T3a", "name": "CPL-SI -> SKKNI", "prodi": "SI", "target": "SKKNI"},
        {"id": "T3b", "name": "CPL-TI -> SKKNI", "prodi": "TI", "target": "SKKNI"},
        {"id": "T4", "name": "SKKNI -> ESCO Skills", "prodi": None, "target": "ESCO"},
        {"id": "T5", "name": "SKKNI -> O*NET", "prodi": None, "target": "ONET"},
    ]
