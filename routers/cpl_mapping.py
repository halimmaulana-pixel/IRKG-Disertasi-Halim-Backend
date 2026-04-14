"""
CPL Mapping router — multi-prodi domain mapping results.
Grouping: per prodi (program studi), bukan per universitas.

Prodi:
  SI (Sistem Informasi)    = UMSU_SI + UI_SI
  TI (Teknologi Informasi) = UMSU_TI + UGM_TI
  IF (Informatika)         = ITK
  TK (Teknik Komputer)     = PENS
"""
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter()

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUTPUTS = BACKEND_DIR / "data" / "outputs"
SOURCE_DIR = BACKEND_DIR / "data" / "raw" / "source_data"

# Prodi definitions — key adalah prodi, bukan universitas
PRODI_DEFS = [
    {"key": "SI", "label": "Sistem Informasi",    "univs": ["UMSU_SI", "UI_SI"]},
    {"key": "TI", "label": "Teknologi Informasi", "univs": ["UMSU_TI", "UGM_TI"]},
    {"key": "IF", "label": "Informatika",          "univs": ["ITK"]},
    {"key": "TK", "label": "Teknik Komputer",      "univs": ["PENS"]},
]

PRODI_ORDER = ["SI", "TI", "IF", "TK"]
FRAMEWORKS  = ["ESCO", "ONET", "SKKNI"]

# Mapping univ (dari file hasil) ke prodi key
UNIV_TO_PRODI = {
    "UMSU_SI": "SI", "UI_SI": "SI",
    "UMSU_TI": "TI", "UGM_TI": "TI",
    "ITK":     "IF",
    "PENS":    "TK",
}

# Label pendek universitas untuk tampil di tabel
UNIV_SHORT = {
    "UMSU_SI": "UMSU", "UI_SI": "UI",
    "UMSU_TI": "UMSU", "UGM_TI": "UGM",
    "ITK": "ITK", "PENS": "PENS",
}


def _load_results() -> pd.DataFrame:
    path = OUTPUTS / "external_cpl_inductive_results.xlsx"
    if not path.exists():
        raise FileNotFoundError("File hasil belum ada: external_cpl_inductive_results.xlsx")
    df = pd.read_excel(path)
    # Tambah kolom prodi
    df["prodi"] = df["univ"].map(UNIV_TO_PRODI).fillna("?")
    return df


@router.get("/summary")
def get_summary():
    """Mean S_sem (top-1) per prodi x framework."""
    try:
        df = _load_results()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    top1 = df[df["rank"] == 1].copy()
    result = []
    for p in PRODI_DEFS:
        sub = top1[top1["prodi"] == p["key"]]
        scores = {}
        for fw in FRAMEWORKS:
            fw_sub = sub[sub["framework"] == fw]
            scores[fw.lower()] = round(float(fw_sub["s_sem"].mean()), 4) if len(fw_sub) else None
        result.append({
            "prodi":   p["key"],
            "label":   p["label"],
            "univs":   p["univs"],
            "n_cpl":   int(sub["cpl_id"].nunique()),
            **scores,
        })
    return result


@router.get("/detail")
def get_detail(prodi: str = None):
    """
    CPL rows with top-1 match per framework.
    prodi: SI | TI | IF | TK | ALL (default ALL)
    """
    try:
        df = _load_results()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    top1 = df[df["rank"] == 1].copy()

    if prodi and prodi != "ALL":
        if prodi not in PRODI_ORDER:
            raise HTTPException(400, f"Prodi tidak dikenal: {prodi}")
        top1 = top1[top1["prodi"] == prodi]

    # Pivot to wide
    pivot = top1.pivot_table(
        index=["prodi", "univ", "cpl_id", "ranah", "cpl_text"],
        columns="framework",
        values=["target_label", "s_sem"],
        aggfunc="first",
    ).reset_index()

    pivot.columns = [
        "_".join(c).strip("_") if c[1] else c[0]
        for c in pivot.columns
    ]

    rows = []
    for _, r in pivot.iterrows():
        prodi_key = r.get("prodi", "?")
        univ_key  = r.get("univ", "")
        row = {
            "prodi":      prodi_key,
            "prodi_label": next((p["label"] for p in PRODI_DEFS if p["key"] == prodi_key), prodi_key),
            "univ":       univ_key,
            "univ_short": UNIV_SHORT.get(univ_key, univ_key),
            "cpl_id":     r.get("cpl_id", ""),
            "ranah":      r.get("ranah", ""),
            "cpl_text":   r.get("cpl_text", ""),
        }
        for fw in FRAMEWORKS:
            lk = f"target_label_{fw}"
            sk = f"s_sem_{fw}"
            row[f"{fw.lower()}_label"] = r.get(lk, "") or ""
            raw_score = r.get(sk, None)
            try:
                row[f"{fw.lower()}_score"] = round(float(raw_score), 4) if raw_score is not None and str(raw_score) != "nan" else None
            except (TypeError, ValueError):
                row[f"{fw.lower()}_score"] = None
        rows.append(row)

    # Sort: prodi order, then cpl_id
    order_map = {p: i for i, p in enumerate(PRODI_ORDER)}
    rows.sort(key=lambda r: (order_map.get(r["prodi"], 99), r["cpl_id"]))

    return rows


@router.get("/ranah-summary")
def get_ranah_summary():
    """Mean S_sem per ranah x framework (all prodi)."""
    try:
        df = _load_results()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    top1 = df[df["rank"] == 1].copy()
    result = []
    for ranah in top1["ranah"].dropna().unique():
        sub = top1[top1["ranah"] == ranah]
        scores = {}
        for fw in FRAMEWORKS:
            fw_sub = sub[sub["framework"] == fw]
            scores[fw.lower()] = round(float(fw_sub["s_sem"].mean()), 4) if len(fw_sub) else None
        result.append({"ranah": ranah, **scores})
    return result


@router.get("/meta")
def get_meta():
    return {
        "prodi": PRODI_DEFS,
        "order": PRODI_ORDER,
        "frameworks": FRAMEWORKS,
        "univ_to_prodi": UNIV_TO_PRODI,
    }
