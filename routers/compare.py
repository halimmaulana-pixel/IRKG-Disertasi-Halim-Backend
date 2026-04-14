# backend/routers/compare.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import CRIResult, CRIByRanah

router = APIRouter()

PRODI_DEFS = [
    {"key": "SI", "label": "Sistem Informasi",    "task_prodi": "SI", "univs": None},
    {"key": "TI", "label": "Teknologi Informasi", "task_prodi": "TI", "univs": ["UMSU", "UGM"]},
    {"key": "IF", "label": "Informatika",          "task_prodi": "TI", "univs": ["ITK"]},
    {"key": "TK", "label": "Teknik Komputer",      "task_prodi": "TI", "univs": ["PENS"]},
]

def _extract_univ(source_id: str) -> str:
    parts = str(source_id).split("_")
    if len(parts) >= 3 and parts[1].upper() not in ("PLO",):
        return parts[1].upper()
    return "UMSU"

def _filter_by_prodi(items, prodi_key: str):
    meta = next((p for p in PRODI_DEFS if p["key"] == prodi_key), None)
    if not meta:
        return []
    filtered = [i for i in items if i.prodi == meta["task_prodi"]]
    if meta["univs"]:
        filtered = [i for i in filtered if _extract_univ(i.source_id) in meta["univs"]]
    return filtered

def _calc_stats(items):
    if not items:
        return {}
    return {
        "cri_mean":    round(sum(i.cri_score for i in items) / len(items), 4),
        "r_esco_mean": round(sum(i.r_esco    for i in items) / len(items), 4),
        "r_onet_mean": round(sum(i.r_onet    for i in items) / len(items), 4),
        "r_skkni_mean":round(sum(i.r_skkni   for i in items) / len(items), 4),
        "n_complete":  sum(1 for i in items if i.cri_flag == "COMPLETE"),
        "n_partial":   sum(1 for i in items if i.cri_flag == "PARTIAL"),
        "n_incomplete":sum(1 for i in items if i.cri_flag == "INCOMPLETE"),
        "n_items": len(items),
        "items": [{"source_id": i.source_id, "ranah": i.ranah,
                   "cri_score": i.cri_score, "cri_flag": i.cri_flag,
                   "r_esco": i.r_esco, "r_onet": i.r_onet, "r_skkni": i.r_skkni}
                  for i in items],
    }

@router.get("/si-ti")
def compare_si_ti(db: Session = Depends(get_db)):
    si = db.query(CRIResult).filter(CRIResult.prodi == "SI").all()
    ti = db.query(CRIResult).filter(CRIResult.prodi == "TI").all()
    return {"SI": _calc_stats(si), "TI": _calc_stats(ti)}

@router.get("/by-prodi")
def compare_by_prodi(db: Session = Depends(get_db)):
    """Perbandingan CRI per prodi (4 prodi)."""
    all_items = db.query(CRIResult).all()
    result = {}
    for p in PRODI_DEFS:
        items = _filter_by_prodi(all_items, p["key"])
        result[p["key"]] = {**_calc_stats(items), "label": p["label"]}
    return result

@router.get("/by-ranah")
def compare_by_ranah(db: Session = Depends(get_db)):
    ranah_data = db.query(CRIByRanah).all()
    return [{"ranah": r.ranah,
             "has_mapping_esco": r.has_mapping_esco,
             "has_mapping_onet": r.has_mapping_onet,
             "has_mapping_skkni": r.has_mapping_skkni} for r in ranah_data]
