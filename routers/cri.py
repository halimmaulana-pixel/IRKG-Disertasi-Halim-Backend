# backend/routers/cri.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import CRIResult, CRIByRanah, AcceptedMapping

router = APIRouter()

# ── Prodi definitions ─────────────────────────────────────────────────────────
# Prodi = program studi. Setiap prodi bisa punya CPL dari beberapa universitas.
# task_prodi = kolom `prodi` di DB (SI atau TI, sesuai task pipeline)
# univs      = universitas mana yang masuk prodi ini (None = semua univ di task tsb)
PRODI_DEFS = [
    {"key": "SI", "label": "Sistem Informasi",    "task_prodi": "SI", "univs": None},
    {"key": "TI", "label": "Teknologi Informasi", "task_prodi": "TI", "univs": ["UMSU", "UGM"]},
    {"key": "IF", "label": "Informatika",          "task_prodi": "TI", "univs": ["ITK"]},
    {"key": "TK", "label": "Teknik Komputer",      "task_prodi": "TI", "univs": ["PENS"]},
]

# Mapping univ → prodi key (untuk label badge di UI)
UNIV_PRODI_MAP = {
    "UMSU": {"SI": "SI",  "TI": "TI"},
    "UI":   {"SI": "SI"},
    "UGM":  {"TI": "TI"},
    "ITK":  {"TI": "IF"},
    "PENS": {"TI": "TK"},
}

UNIV_LABELS = {
    "UMSU": "UMSU", "UI": "UI", "UGM": "UGM", "ITK": "ITK", "PENS": "PENS",
}


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


@router.get("/by-prodi/summary")
def get_cri_by_prodi_summary(db: Session = Depends(get_db)):
    """Ringkasan CRI per prodi (4 prodi)."""
    all_items = db.query(CRIResult).all()
    result = []
    for p in PRODI_DEFS:
        items = _filter_by_prodi(all_items, p["key"])
        if not items:
            result.append({**p, "n_items": 0, "cri_mean": None,
                           "r_esco_mean": None, "r_onet_mean": None, "r_skkni_mean": None,
                           "n_complete": 0, "n_partial": 0, "n_incomplete": 0})
            continue
        result.append({
            **p,
            "n_items":      len(items),
            "cri_mean":     round(sum(i.cri_score for i in items) / len(items), 4),
            "r_esco_mean":  round(sum(i.r_esco    for i in items) / len(items), 4),
            "r_onet_mean":  round(sum(i.r_onet    for i in items) / len(items), 4),
            "r_skkni_mean": round(sum(i.r_skkni   for i in items) / len(items), 4),
            "n_complete":   sum(1 for i in items if i.cri_flag == "COMPLETE"),
            "n_partial":    sum(1 for i in items if i.cri_flag == "PARTIAL"),
            "n_incomplete": sum(1 for i in items if i.cri_flag == "INCOMPLETE"),
        })
    return result


@router.get("/by-prodi/{prodi_key}")
def get_cri_by_prodi_key(prodi_key: str, db: Session = Depends(get_db)):
    """CRI per CPL untuk satu prodi. prodi_key: SI | TI | IF | TK"""
    all_items = db.query(CRIResult).order_by(CRIResult.source_id).all()
    items = _filter_by_prodi(all_items, prodi_key)
    return [_serialize_item(i) for i in items]


@router.get("/{prodi}")
def get_cri_by_prodi(prodi: str, db: Session = Depends(get_db)):
    """CRI per CPL item untuk satu task-prodi (SI atau TI)."""
    items = db.query(CRIResult).filter(
        CRIResult.prodi == prodi
    ).order_by(CRIResult.source_id).all()
    return [_serialize_item(i) for i in items]


def _serialize_item(item: CRIResult) -> dict:
    univ = _extract_univ(item.source_id)
    return {
        "source_id":      item.source_id,
        "univ":           univ,
        "univ_label":     UNIV_LABELS.get(univ, univ),
        "prodi":          item.prodi,
        "ranah":          item.ranah,
        "r_esco":         item.r_esco,
        "r_onet":         item.r_onet,
        "r_skkni":        item.r_skkni,
        "cri_score":      item.cri_score,
        "cri_flag":       item.cri_flag,
        "top_esco_label": item.top_esco_label,
        "top_onet_label": item.top_onet_label,
        "top_skkni_label":item.top_skkni_label,
        "n_ok_esco":      item.n_ok_esco,
        "n_ok_onet":      item.n_ok_onet,
        "n_ok_skkni":     item.n_ok_skkni,
        "narasi":         generate_narasi(item),
    }


def generate_narasi(item: CRIResult) -> str:
    score_pct = round(item.cri_score * 100, 1)
    if item.cri_flag == "INCOMPLETE":
        return (
            f"CPL ini tidak terpetakan ke satupun framework kompetensi global maupun nasional. "
            f"Hal ini mengindikasikan bahwa deskripsi CPL menggunakan bahasa yang terlalu abstrak "
            f"atau kultural-spesifik sehingga tidak dapat dijembatani secara semantik. "
            f"Rekomendasi: tambahkan deskriptor perilaku yang operasional dan konteks domain TI yang eksplisit."
        )
    parts = []
    if item.r_esco > 0.35:
        parts.append(f"kesesuaian tinggi dengan ESCO ({round(item.r_esco*100,1)}%)")
        if item.top_esco_label:
            parts.append(f"pemetaan terbaik ke '{item.top_esco_label}'")
    elif item.r_esco > 0:
        parts.append(f"kesesuaian parsial dengan ESCO ({round(item.r_esco*100,1)}%)")
    else:
        parts.append("tidak terpetakan ke ESCO")
    if item.r_onet > 0.35:
        parts.append(f"selaras dengan O*NET ({round(item.r_onet*100,1)}%)")
    elif item.r_onet > 0:
        parts.append(f"kesesuaian terbatas dengan O*NET ({round(item.r_onet*100,1)}%)")
    else:
        parts.append("belum terpetakan ke O*NET")
    if item.r_skkni > 0.35:
        parts.append(f"selaras dengan SKKNI ({round(item.r_skkni*100,1)}%)")
    elif item.r_skkni > 0:
        parts.append(f"kesesuaian parsial dengan SKKNI ({round(item.r_skkni*100,1)}%)")
    narasi = f"CRI {score_pct}% ({item.cri_flag}): " + "; ".join(parts) + "."
    if item.r_esco == 0 and item.r_onet == 0 and item.r_skkni > 0:
        narasi += " Rekomendasi: perkuat deskripsi dengan terminologi teknis berbahasa Inggris."
    return narasi


@router.get("/ranah/summary")
def get_cri_by_ranah(db: Session = Depends(get_db)):
    items = db.query(CRIByRanah).all()
    return [{"ranah": i.ranah, "n_items": i.n_items,
             "has_mapping_esco": i.has_mapping_esco,
             "has_mapping_onet": i.has_mapping_onet,
             "has_mapping_skkni": i.has_mapping_skkni,
             "mean_sfinal_esco": i.mean_sfinal_esco,
             "mean_sfinal_onet": i.mean_sfinal_onet,
             "mean_sfinal_skkni": i.mean_sfinal_skkni} for i in items]


@router.get("/compare/si-ti")
def compare_prodi(db: Session = Depends(get_db)):
    si = db.query(CRIResult).filter(CRIResult.prodi == "SI").all()
    ti = db.query(CRIResult).filter(CRIResult.prodi == "TI").all()

    def summarize(items):
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
            "items": [{"source_id": i.source_id, "ranah": i.ranah,
                       "cri_score": i.cri_score, "cri_flag": i.cri_flag,
                       "r_esco": i.r_esco, "r_onet": i.r_onet, "r_skkni": i.r_skkni}
                      for i in items],
        }
    return {"SI": summarize(si), "TI": summarize(ti)}


@router.get("/{source_id}/mappings")
def get_cpl_mappings_detail(
    source_id: str,
    config: str = Query("v1.2"),
    db: Session = Depends(get_db)
):
    all_mappings = db.query(AcceptedMapping).filter(
        AcceptedMapping.source_id == source_id,
        AcceptedMapping.config == config,
        AcceptedMapping.forced_top1 == False,
    ).order_by(AcceptedMapping.s_final.desc()).all()

    esco  = [m for m in all_mappings if m.target_type == "ESCO"]
    onet  = [m for m in all_mappings if m.target_type == "ONET"]
    skkni = [m for m in all_mappings if m.target_type == "SKKNI"]

    def serialize(mappings, limit=10):
        return [{"target_id": m.target_id, "target_label": m.target_label,
                 "s_sem": round(m.s_sem, 4), "s_gr": round(m.s_gr, 4),
                 "s_con": round(m.s_con, 4), "s_final": round(m.s_final, 4)}
                for m in mappings[:limit]]

    return {
        "source_id": source_id, "config": config,
        "summary": {"n_esco": len(esco), "n_onet": len(onet),
                    "n_skkni": len(skkni), "n_total": len(all_mappings)},
        "esco": serialize(esco), "onet": serialize(onet), "skkni": serialize(skkni, 15),
    }
