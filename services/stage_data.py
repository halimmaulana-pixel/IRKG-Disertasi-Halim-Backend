"""
Stage data service — returns rich, visualizable data for each pipeline stage.
"""
import json
import pickle
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUTPUTS = BACKEND_DIR / "data" / "outputs"
ACCEPTED = OUTPUTS / "accepted_mappings"


def get_stage_data(stage_id: str) -> dict:
    handlers = {
        "stage00": _stage00,
        "stage01": _stage01,
        "stage02": _stage02,
        "stage03": _stage03,
        "stage04": _stage04,
        "stage05": _stage05,
        "stage05b": _stage05b,
        "t10": _t10,
        "stage06": _stage06,
        "db": _db,
    }
    handler = handlers.get(stage_id)
    if not handler:
        return {"stage_id": stage_id, "type": "empty", "title": stage_id,
                "message": "Tidak ada data visualisasi untuk stage ini."}
    try:
        return handler()
    except Exception as exc:
        return {"stage_id": stage_id, "type": "error", "title": stage_id, "message": str(exc)}


# ---------- Stage 00 ----------
def _stage00():
    csv = OUTPUTS / "irkg_domain_filter.csv"
    if not csv.exists():
        return {"type": "error", "title": "Domain Filter", "message": "File tidak ditemukan."}
    df = pd.read_csv(csv)

    counts = df.groupby(["prodi", "domain_status"]).size().reset_index(name="n").to_dict(orient="records")

    stats = df.groupby("prodi").agg(
        total=("node_id", "count"),
        n_whitelist=("in_whitelist", "sum"),
        mean_sim=("sim_score", "mean"),
        mean_scon=("s_con", "mean"),
    ).reset_index()
    stats["mean_sim"] = stats["mean_sim"].round(4)
    stats["mean_scon"] = stats["mean_scon"].round(4)
    stats_list = stats.to_dict(orient="records")

    samples = (
        df.nlargest(30, "s_con")[["prodi", "node_id", "s_con", "domain_status", "sim_score", "in_whitelist"]]
        .assign(sim_score=lambda d: d.sim_score.round(4))
        .to_dict(orient="records")
    )

    return {
        "stage_id": "stage00",
        "type": "domain_filter",
        "title": "Domain Filter — S_con Pre-compute",
        "total_rows": len(df),
        "counts_by_status": counts,
        "stats_by_prodi": stats_list,
        "samples": samples,
    }


# ---------- Stage 01 ----------
def _stage01():
    tasks = ["T1a", "T1b", "T2a", "T2b", "T3a", "T3b", "T4", "T5"]
    rows = []
    for t in tasks:
        pkl = OUTPUTS / f"vectorizer_{t}.pkl"
        if not pkl.exists():
            rows.append({"task": t, "exists": False})
            continue
        try:
            with open(pkl, "rb") as f:
                vec = pickle.load(f)
            import numpy as np
            vocab = vec.vocabulary_      # {term: col_index}
            idf = vec.idf_               # array of IDF values

            vocab_size = len(vocab)
            idf_min = round(float(idf.min()), 3)
            idf_max = round(float(idf.max()), 3)
            idf_mean = round(float(idf.mean()), 3)

            # IDF distribution buckets
            idf_dist = {
                "1–2 (stopwords)":   int(((idf >= 1) & (idf < 2)).sum()),
                "2–4 (common)":      int(((idf >= 2) & (idf < 4)).sum()),
                "4–6 (informative)": int(((idf >= 4) & (idf < 6)).sum()),
                "6–8 (specific)":    int(((idf >= 6) & (idf < 8)).sum()),
                "8–10 (rare)":       int((idf >= 8).sum()),
            }

            # Top terms by IDF (most distinctive / rare)
            sorted_by_idf = sorted(vocab.items(), key=lambda x: idf[x[1]], reverse=True)
            top_rare = [{"term": term, "idf": round(float(idf[idx]), 3)}
                        for term, idx in sorted_by_idf[:30]]

            # Bottom terms (common, low IDF — effectively stopwords not filtered)
            top_common = [{"term": term, "idf": round(float(idf[idx]), 3)}
                          for term, idx in sorted_by_idf[-20:]]

            # Mid-IDF: domain-informative terms (IDF 3–6)
            mid_terms = [(term, round(float(idf[idx]), 3))
                         for term, idx in vocab.items() if 3.0 < idf[idx] < 6.0]
            mid_terms.sort(key=lambda x: x[1])
            top_mid = [{"term": t2, "idf": idf2} for t2, idf2 in mid_terms[:40]]

            rows.append({
                "task": t,
                "exists": True,
                "vocab_size": vocab_size,
                "max_features": getattr(vec, "max_features", None),
                "ngram_range": list(getattr(vec, "ngram_range", [1, 1])),
                "min_df": getattr(vec, "min_df", None),
                "max_df": getattr(vec, "max_df", None),
                "sublinear_tf": getattr(vec, "sublinear_tf", False),
                "size_kb": round(pkl.stat().st_size / 1024, 1),
                "idf_min": idf_min,
                "idf_max": idf_max,
                "idf_mean": idf_mean,
                "idf_distribution": idf_dist,
                "top_rare_terms": top_rare,
                "top_common_terms": top_common,
                "top_mid_terms": top_mid,
            })
        except Exception as e:
            rows.append({"task": t, "exists": True, "error": str(e)})
    return {
        "stage_id": "stage01",
        "type": "vectorizers",
        "title": "TF-IDF Vectorizer — Build & Analisis Vocabulary",
        "process_steps": [
            {"step": 1, "name": "Tokenisasi", "desc": "Corpus target dipecah menjadi token (unigram + bigram sesuai ngram_range)"},
            {"step": 2, "name": "Hitung TF", "desc": "Term Frequency per dokumen — sublinear_tf=True → TF = 1 + log(count)"},
            {"step": 3, "name": "Hitung IDF", "desc": "IDF = log((1+N)/(1+df)) + 1, smooth_idf=True untuk hindari zero-division"},
            {"step": 4, "name": "Seleksi Fitur", "desc": "Ambil max_features token teratas berdasarkan frekuensi; filter min_df/max_df"},
            {"step": 5, "name": "Normalisasi L2", "desc": "Setiap vektor dinormalisasi: ||v||=1 → cosine similarity = dot product"},
        ],
        "vectorizers": rows,
    }


# ---------- Stage 02 ----------
def _stage02():
    tasks = ["T1a", "T1b", "T2a", "T2b", "T3a", "T3b", "T4", "T5"]
    results = []
    for t in tasks:
        csv = ACCEPTED / f"irkg_accepted_{t}_v1.2.csv"
        if not csv.exists():
            continue
        df = pd.read_csv(csv)
        top = (
            df.nlargest(8, "s_sem")[["source_id", "target_label", "s_sem", "s_gr", "s_con", "s_final"]]
            .round(4)
            .to_dict(orient="records")
        )
        results.append({
            "task": t,
            "n_total": len(df),
            "n_sources": int(df["source_id"].nunique()),
            "mean_s_sem": round(float(df["s_sem"].mean()), 4),
            "top": top,
        })
    return {
        "stage_id": "stage02",
        "type": "candidates",
        "title": "Top-k Candidate Generation (config v1.2)",
        "tasks": results,
    }


# ---------- Stage 03 ----------
def _stage03():
    tasks = ["T1a", "T1b", "T2a", "T2b"]  # ESCO tasks only — have S_gr
    results = []
    for t in tasks:
        csv = ACCEPTED / f"irkg_accepted_{t}_v1.2.csv"
        if not csv.exists():
            continue
        df = pd.read_csv(csv)
        sgr = df["s_gr"]
        dist = {
            "zero": int((sgr == 0).sum()),
            "low (0–0.1)": int(((sgr > 0) & (sgr <= 0.1)).sum()),
            "mid (0.1–0.3)": int(((sgr > 0.1) & (sgr <= 0.3)).sum()),
            "high (>0.3)": int((sgr > 0.3).sum()),
        }
        results.append({
            "task": t,
            "mean_s_gr": round(float(sgr.mean()), 4),
            "max_s_gr": round(float(sgr.max()), 4),
            "pct_nonzero": round(float((sgr > 0).mean() * 100), 1),
            "distribution": dist,
        })
    return {
        "stage_id": "stage03",
        "type": "graph_cohesion",
        "title": "Graph Cohesion (S_gr) Distribution",
        "tasks": results,
    }


# ---------- Stage 04 ----------
def _stage04():
    tasks = ["T1a", "T1b", "T2a", "T2b", "T3a", "T3b", "T4", "T5"]
    results = []
    for t in tasks:
        csv = ACCEPTED / f"irkg_accepted_{t}_v1.2.csv"
        if not csv.exists():
            continue
        df = pd.read_csv(csv)
        top = (
            df.nlargest(10, "s_final")[
                ["source_id", "target_label", "s_sem", "s_gr", "s_con", "s_final", "forced_top1"]
            ]
            .round({"s_sem": 4, "s_gr": 4, "s_con": 4, "s_final": 4})
            .to_dict(orient="records")
        )
        results.append({
            "task": t,
            "n_accepted": len(df),
            "n_forced": int(df["forced_top1"].sum()),
            "mean_s_final": round(float(df["s_final"].mean()), 4),
            "max_s_final": round(float(df["s_final"].max()), 4),
            "top10": top,
        })
    return {
        "stage_id": "stage04",
        "type": "hybrid_scoring",
        "title": "Hybrid Scoring + Acceptance Gate (v1.2)",
        "tasks": results,
    }


# ---------- Stage 05 ----------
def _stage05():
    xlsx = OUTPUTS / "irkg_ablation_final.xlsx"
    if not xlsx.exists():
        return {"type": "error", "title": "Ablation", "message": "File tidak ditemukan."}
    df = pd.read_excel(xlsx)
    for col in df.select_dtypes("float").columns:
        df[col] = df[col].round(4)
    records = []
    for r in df.to_dict(orient="records"):
        clean = {}
        for k, v in r.items():
            clean[k] = v.item() if hasattr(v, "item") else v
        records.append(clean)
    # best config per task
    best = df.loc[df.groupby("task")["selection_objective"].idxmax()]
    best_list = []
    for r in best[["task", "config", "selection_objective", "mean_final_score", "source_coverage"]].to_dict(orient="records"):
        clean = {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()}
        best_list.append(clean)
    return {
        "stage_id": "stage05",
        "type": "ablation",
        "title": "Ablation Evaluation — Semua Task × Config",
        "columns": list(df.columns),
        "rows": records,
        "best_per_task": best_list,
    }


# ---------- Stage 05b ----------
def _stage05b():
    csv = OUTPUTS / "irkg_coverage_by_ranah_summary.csv"
    detail_csv = OUTPUTS / "irkg_coverage_by_ranah_detail.csv"
    univ_csv   = OUTPUTS / "irkg_coverage_by_univ.csv"
    if not csv.exists():
        return {"type": "error", "title": "Coverage by Ranah", "message": "File tidak ditemukan."}
    summary = pd.read_csv(csv).round(4).to_dict(orient="records")
    detail = []
    if detail_csv.exists():
        df_d = pd.read_csv(detail_csv)
        for col in df_d.select_dtypes("float").columns:
            df_d[col] = df_d[col].round(4)
        detail = df_d.to_dict(orient="records")
    univ_summary = []
    if univ_csv.exists():
        df_u = pd.read_csv(univ_csv).round(4)
        univ_summary = df_u.to_dict(orient="records")
    return {
        "stage_id": "stage05b",
        "type": "coverage_by_ranah",
        "title": "Coverage CPL by Ranah",
        "summary": summary,
        "detail": detail,
        "univ_summary": univ_summary,
    }


# ---------- T10 CRI ----------
def _t10():
    xlsx = OUTPUTS / "cri_results.xlsx"
    if not xlsx.exists():
        return {"type": "error", "title": "CRI", "message": "File tidak ditemukan."}
    df = pd.read_excel(xlsx)
    keep = ["source_id", "univ", "prodi", "ranah", "deskripsi_cpl", "cri_score", "cri_flag",
            "r_esco", "r_onet", "r_skkni", "n_ok_esco", "n_ok_onet", "n_ok_skkni",
            "top_esco_label", "top_esco_score", "top_onet_label", "top_onet_score",
            "top_skkni_label", "top_skkni_score"]
    keep = [c for c in keep if c in df.columns]
    for col in df[keep].select_dtypes("float").columns:
        df[col] = df[col].round(4)
    records = []
    for r in df[keep].to_dict(orient="records"):
        clean = {}
        for k, v in r.items():
            if hasattr(v, "item"):
                clean[k] = v.item()
            elif isinstance(v, float) and v != v:  # NaN
                clean[k] = None
            else:
                clean[k] = v
        records.append(clean)
    # summary per prodi (SI/TI)
    summary = {}
    for p in ["SI", "TI"]:
        sub = df[df["prodi"] == p]
        if len(sub) == 0:
            continue
        summary[p] = {
            "mean_cri": round(float(sub["cri_score"].mean()), 4),
            "n_complete": int((sub["cri_flag"] == "COMPLETE").sum()),
            "n_partial": int((sub["cri_flag"] == "PARTIAL").sum()),
            "n_incomplete": int((sub["cri_flag"] == "INCOMPLETE").sum()),
        }

    # summary per universitas — ekstrak dari source_id atau kolom univ
    def _univ_from_sid(sid):
        parts = str(sid).split("_")
        if len(parts) >= 3 and parts[1].upper() not in ("PLO",):
            return parts[1].upper()
        return "UMSU"

    if "univ" not in df.columns:
        df["univ"] = df["source_id"].apply(_univ_from_sid)
    if "prodi" not in df.columns:
        df["prodi"] = df["source_id"].apply(lambda x: x.split("_")[0])

    UNIV_ORDER = ["UMSU", "UI", "ITK", "PENS", "UGM"]
    UNIV_LABEL = {
        "UMSU_SI": "UMSU – SI", "UI_SI": "UI – SI",
        "UMSU_TI": "UMSU – TI", "ITK_TI": "ITK – IF",
        "PENS_TI": "PENS – TK", "UGM_TI": "UGM – TI",
    }
    summary_univ = []
    for _, grp in df.groupby(["univ", "prodi"]):
        univ = grp["univ"].iloc[0]
        prodi = grp["prodi"].iloc[0]
        key = f"{univ}_{prodi}"
        summary_univ.append({
            "key": key,
            "label": UNIV_LABEL.get(key, key),
            "univ": univ,
            "prodi": prodi,
            "mean_cri": round(float(grp["cri_score"].mean()), 4),
            "mean_esco": round(float(grp["r_esco"].mean()), 4) if "r_esco" in grp.columns else None,
            "mean_onet": round(float(grp["r_onet"].mean()), 4) if "r_onet" in grp.columns else None,
            "mean_skkni": round(float(grp["r_skkni"].mean()), 4) if "r_skkni" in grp.columns else None,
            "n_items": len(grp),
            "n_complete": int((grp["cri_flag"] == "COMPLETE").sum()),
            "n_partial": int((grp["cri_flag"] == "PARTIAL").sum()),
            "n_incomplete": int((grp["cri_flag"] == "INCOMPLETE").sum()),
        })

    return {
        "stage_id": "t10",
        "type": "cri",
        "title": "Career Readiness Index (CRI) per CPL",
        "summary": summary,
        "summary_univ": summary_univ,
        "rows": records,
    }


# ---------- Stage 06 ----------
def _stage06():
    path = OUTPUTS / "ecv_results.xlsx"
    if not path.exists():
        path = OUTPUTS / "ecv_results.csv"
    if not path.exists():
        return {"type": "error", "title": "ECV", "message": "File tidak ditemukan."}
    df = pd.read_excel(path) if path.suffix == ".xlsx" else pd.read_csv(path)
    for col in df.select_dtypes("float").columns:
        df[col] = df[col].round(4)
    records = []
    for r in df.to_dict(orient="records"):
        clean = {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()}
        records.append(clean)
    return {
        "stage_id": "stage06",
        "type": "ecv",
        "title": "External Consistency Validation (ECV)",
        "columns": list(df.columns),
        "rows": records,
    }


# ---------- DB ----------
def _db():
    db_path = BACKEND_DIR / "data" / "db" / "irkg.db"
    summary_path = OUTPUTS / "irkg_summary.json"
    result: dict = {
        "stage_id": "db",
        "type": "db_stats",
        "title": "Load Outputs → Database",
    }
    if db_path.exists():
        result["db_size_mb"] = round(db_path.stat().st_size / 1024 / 1024, 2)
    if summary_path.exists():
        with open(summary_path) as f:
            result["summary"] = json.load(f)
    files = []
    for p in [
        ACCEPTED,
        OUTPUTS / "cri_results.xlsx",
        OUTPUTS / "ecv_results.xlsx",
        OUTPUTS / "irkg_ablation_final.xlsx",
        OUTPUTS / "irkg_domain_filter.csv",
    ]:
        if p.exists():
            if p.is_dir():
                n = sum(1 for _ in p.iterdir())
                files.append({"name": p.name, "type": "dir", "n_files": n})
            else:
                files.append({"name": p.name, "type": "file", "size_kb": round(p.stat().st_size / 1024, 1)})
    result["output_files"] = files
    return result
