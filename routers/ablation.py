# backend/routers/ablation.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AblationResult

router = APIRouter()

CONFIG_ORDER = ["v0.9", "v1.1", "v1.2", "v1.3", "v1.4"]


@router.get("/")
def get_ablation(db: Session = Depends(get_db)):
    results = db.query(AblationResult).order_by(
        AblationResult.task, AblationResult.config
    ).all()

    heatmap = {}
    present_cfg = set()
    per_cfg_scores = {}

    for r in results:
        present_cfg.add(r.config)
        if r.task not in heatmap:
            heatmap[r.task] = {}
        heatmap[r.task][r.config] = {
            "acceptance_rate": r.acceptance_rate,
            "source_coverage": r.source_coverage,
            "mean_final_score": r.mean_final_score,
            "forced_top1_ratio": r.forced_top1_ratio,
            "selection_objective": r.selection_objective,
            "esco_target": r.esco_target,
            "config_name": r.config_name,
        }
        per_cfg_scores.setdefault(r.config, []).append(float(r.selection_objective or 0.0))

    configs = [c for c in CONFIG_ORDER if c in present_cfg]
    if not configs:
        configs = sorted(present_cfg)

    tasks_esco = ["T1a", "T1b", "T4"]
    tasks_nonesco = ["T2a", "T2b", "T3a", "T3b", "T5"]

    best_config = None
    if per_cfg_scores:
        best_config = max(per_cfg_scores.items(), key=lambda x: sum(x[1]) / max(len(x[1]), 1))[0]

    return {
        "heatmap": heatmap,
        "configs": configs,
        "tasks_esco": tasks_esco,
        "tasks_nonesco": tasks_nonesco,
        "best_config": best_config or "v1.2",
    }
