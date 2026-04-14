# backend/routers/domain.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import DomainFilterResult, KGNode

router = APIRouter()

PRODI_LIST = ["SI", "TI", "CS", "SE", "CE", "DS"]


@router.get("/stats")
def get_domain_stats(db: Session = Depends(get_db)):
    """Statistik ringkas Domain Filter Stage00."""
    total_core = db.query(func.count(DomainFilterResult.id)).filter(
        DomainFilterResult.domain_status == "core"
    ).scalar() or 0

    total_adjacent = db.query(func.count(DomainFilterResult.id)).filter(
        DomainFilterResult.domain_status == "adjacent"
    ).scalar() or 0

    total_outside = db.query(func.count(DomainFilterResult.id)).filter(
        DomainFilterResult.domain_status == "outside"
    ).scalar() or 0

    total = total_core + total_adjacent + total_outside
    coverage_rate = round((total_core + total_adjacent) / total, 4) if total > 0 else 0.0

    return {
        "total_prodi": len(PRODI_LIST),
        "total_core_uris": total_core,
        "total_adjacent_uris": total_adjacent,
        "total_outside": total_outside,
        "coverage_rate": coverage_rate,
        "last_run_at": None,
    }


@router.get("/overlap")
def get_domain_overlap(db: Session = Depends(get_db)):
    """Matrix overlap 6x6 — berapa ESCO skill yang dibagi antara dua prodi."""
    result = []
    for prodi_a in PRODI_LIST:
        ids_a = set(
            r.node_id for r in db.query(DomainFilterResult.node_id).filter(
                DomainFilterResult.prodi == prodi_a,
                DomainFilterResult.domain_status.in_(["core", "adjacent"])
            ).all()
        )
        for prodi_b in PRODI_LIST:
            ids_b = set(
                r.node_id for r in db.query(DomainFilterResult.node_id).filter(
                    DomainFilterResult.prodi == prodi_b,
                    DomainFilterResult.domain_status.in_(["core", "adjacent"])
                ).all()
            )
            overlap = len(ids_a & ids_b)
            denom = len(ids_a) if ids_a else 0
            pct = round(overlap / denom, 4) if denom > 0 else 0.0
            result.append({
                "prodi_a": prodi_a,
                "prodi_b": prodi_b,
                "overlap_count": overlap,
                "overlap_pct": pct,
            })
    return result


@router.get("/s_con_distribution")
def get_s_con_distribution(
    config: str = Query("v1.0"),
    db: Session = Depends(get_db),
):
    """Distribusi S_con per config: jumlah node dengan s_con 1.0 / 0.5 / 0.0."""
    rows = db.query(DomainFilterResult).filter(
        DomainFilterResult.config == config
    ).all()

    n_1_0 = sum(1 for r in rows if r.s_con == 1.0)
    n_0_5 = sum(1 for r in rows if r.s_con == 0.5)
    n_0_0 = sum(1 for r in rows if r.s_con == 0.0)
    total = len(rows)

    return {
        "config": config,
        "n_1_0": n_1_0,
        "n_0_5": n_0_5,
        "n_0_0": n_0_0,
        "pct_1_0": round(n_1_0 / total, 4) if total > 0 else 0.0,
        "pct_0_5": round(n_0_5 / total, 4) if total > 0 else 0.0,
        "pct_0_0": round(n_0_0 / total, 4) if total > 0 else 0.0,
        "total": total,
    }


@router.get("/node-status")
def get_node_domain_status(
    node_id: str = Query(...),
    prodi: str = Query(...),
    db: Session = Depends(get_db),
):
    """Status domain satu ESCO node terhadap prodi tertentu."""
    row = db.query(DomainFilterResult).filter(
        DomainFilterResult.node_id == node_id,
        DomainFilterResult.prodi == prodi,
    ).first()

    if not row:
        return {"node_id": node_id, "prodi": prodi, "status": "outside", "s_con": 0.0}

    return {
        "node_id": row.node_id,
        "prodi": row.prodi,
        "status": row.domain_status,
        "s_con": row.s_con,
    }


@router.get("/{prodi}")
def get_domain_by_prodi(
    prodi: str,
    db: Session = Depends(get_db),
):
    """Detail domain filter untuk satu prodi: core + adjacent uris dan top 20 skills per kategori."""
    prodi_upper = prodi.upper()

    core_rows = db.query(DomainFilterResult).filter(
        DomainFilterResult.prodi == prodi_upper,
        DomainFilterResult.domain_status == "core",
    ).order_by(DomainFilterResult.sim_score.desc()).all()

    adjacent_rows = db.query(DomainFilterResult).filter(
        DomainFilterResult.prodi == prodi_upper,
        DomainFilterResult.domain_status == "adjacent",
    ).order_by(DomainFilterResult.sim_score.desc()).all()

    def enrich(rows):
        node_ids = [r.node_id for r in rows]
        nodes = {n.id: n.label for n in db.query(KGNode).filter(KGNode.id.in_(node_ids)).all()}
        return [
            {"node_id": r.node_id, "label": nodes.get(r.node_id, r.node_id),
             "s_con": r.s_con, "sim_score": r.sim_score}
            for r in rows
        ]

    active_config = core_rows[0].config if core_rows else (adjacent_rows[0].config if adjacent_rows else None)
    return {
        "prodi": prodi_upper,
        "config": active_config,
        "n_core": len(core_rows),
        "n_adjacent": len(adjacent_rows),
        "top_core": enrich(core_rows),
        "top_adjacent": enrich(adjacent_rows),
    }
