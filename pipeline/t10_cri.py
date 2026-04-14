# t10_cri.py - Pipeline IR-KG v1.1
"""
CRI-KG: Career Readiness Index berbasis Knowledge Graph.
Input: accepted mappings dari config terbaik (v1.2)
Formula: CRI(cᵢ) = 0.40·R_ESCO + 0.35·R_ONET + 0.25·R_SKKNI

v1.1 Update: Tambah kolom diagnostik (n_ok_*, has_*_forced)
v1.2 Update: Ekstrak univ dari source_id untuk analisis per-universitas
"""
import pandas as pd
import numpy as np
from config import OUTPUT_DIR, CRI_WEIGHTS, CRI_BASIS_CONFIG, TASK_DEFINITIONS
from data_loader import load_cpl


def _extract_univ(source_id: str) -> str:
    """
    Ekstrak kode universitas dari source_id.
    Format: '{PRODI}_{UNIV}_PLO-N'  e.g. 'SI_UMSU_PLO-1' -> 'UMSU'
    Legacy (sebelum merge): 'SI_PLO-1' -> 'UMSU' (default)
    """
    parts = source_id.split("_")
    # parts[0]=PRODI, parts[1]=UNIV, parts[2+]=PLO-N
    if len(parts) >= 3 and parts[1].upper() not in ("PLO",):
        return parts[1].upper()
    # Legacy: single-univ format SI_PLO-1 -> UMSU
    return "UMSU"


def compute_cri(all_results: dict, basis_config: str = CRI_BASIS_CONFIG) -> pd.DataFrame:
    """
    Hitung CRI untuk semua CPL items.
    Hanya gunakan accepted mappings dari basis_config (default v1.2).
    FORCED_TOP1 dikecualikan dari perhitungan R.
    """
    cfg_results = all_results[basis_config]
    w_E = CRI_WEIGHTS["w_E"]
    w_O = CRI_WEIGHTS["w_O"]
    w_S = CRI_WEIGHTS["w_S"]

    # Task mapping per prodi
    task_map = {
        "SI": {"ESCO": "T1a", "ONET": "T2a", "SKKNI": "T3a"},
        "TI": {"ESCO": "T1b", "ONET": "T2b", "SKKNI": "T3b"},
    }

    results = []

    for prodi, tasks in task_map.items():
        cpl_df = load_cpl(prodi)

        for _, cpl_row in cpl_df.iterrows():
            src_id = cpl_row["id"]
            src_text = cpl_row["deskripsi_cpl"]

            R = {}
            top_matches = {}
            
            # v1.1: Diagnostic counters
            n_ok = {"ESCO": 0, "ONET": 0, "SKKNI": 0}
            has_forced = {"ESCO": False, "ONET": False, "SKKNI": False}

            for fw, task_id in tasks.items():
                if task_id not in cfg_results:
                    R[fw] = 0.0
                    top_matches[fw] = {"id": None, "label": None, "score": None}
                    continue

                task_df = cfg_results[task_id]
                # Filter: source + OK (bukan FORCED_TOP1)
                ok_maps = task_df[
                    (task_df["source_id"] == src_id) &
                    (~task_df["forced_top1"])
                ]
                # Filter: forced only
                forced_maps = task_df[
                    (task_df["source_id"] == src_id) &
                    (task_df["forced_top1"] == True)
                ]
                
                n_ok[fw] = len(ok_maps)
                has_forced[fw] = (len(ok_maps) == 0) and (len(forced_maps) > 0)

                if len(ok_maps) > 0:
                    R[fw] = round(ok_maps["s_final"].mean(), 4)
                    best = ok_maps.loc[ok_maps["s_final"].idxmax()]
                    top_matches[fw] = {
                        "id": best["target_id"],
                        "label": best.get("target_label", ""),
                        "score": round(float(best["s_final"]), 4)
                    }
                else:
                    R[fw] = 0.0
                    if has_forced[fw]:
                        # v1.1: Use forced mapping as top match (with flag)
                        best_f = forced_maps.loc[forced_maps["s_final"].idxmax()]
                        top_matches[fw] = {
                            "id": best_f["target_id"],
                            "label": best_f.get("target_label", ""),
                            "score": round(float(best_f["s_final"]), 4)
                        }
                    else:
                        top_matches[fw] = {"id": None, "label": None, "score": None}

            # Hitung CRI score
            cri_score = round(w_E * R["ESCO"] + w_O * R["ONET"] + w_S * R["SKKNI"], 4)

            # Tentukan flag
            n_zero = sum(1 for v in R.values() if v == 0.0)
            if n_zero == 0:
                flag = "COMPLETE"
            elif n_zero == len(R):
                flag = "INCOMPLETE"
            else:
                flag = "PARTIAL"

            results.append({
                "source_id": src_id,
                "univ": _extract_univ(src_id),
                "prodi": prodi,
                "ranah": cpl_row["ranah"],
                "deskripsi_cpl": src_text,
                "r_esco": R["ESCO"],
                "r_onet": R["ONET"],
                "r_skkni": R["SKKNI"],
                "cri_score": cri_score,
                "cri_flag": flag,
                "config_basis": basis_config,
                "w_e": w_E, "w_o": w_O, "w_s": w_S,
                # v1.1: Diagnostic columns
                "n_ok_esco": n_ok["ESCO"],
                "n_ok_onet": n_ok["ONET"],
                "n_ok_skkni": n_ok["SKKNI"],
                "has_esco_forced": has_forced["ESCO"],
                "has_onet_forced": has_forced["ONET"],
                "has_skkni_forced": has_forced["SKKNI"],
                "top_esco_id": top_matches["ESCO"]["id"],
                "top_esco_label": top_matches["ESCO"]["label"],
                "top_esco_score": top_matches["ESCO"]["score"],
                "top_onet_id": top_matches["ONET"]["id"],
                "top_onet_label": top_matches["ONET"]["label"],
                "top_onet_score": top_matches["ONET"]["score"],
                "top_skkni_id": top_matches["SKKNI"]["id"],
                "top_skkni_label": top_matches["SKKNI"]["label"],
                "top_skkni_score": top_matches["SKKNI"]["score"],
            })

    return pd.DataFrame(results)


def aggregate_to_prodi(cri_df: pd.DataFrame) -> pd.DataFrame:
    """Agregasi CRI dari level butir CPL ke level program studi (SI/TI)."""
    agg = cri_df.groupby("prodi").agg(
        cri_prodi=("cri_score", "mean"),
        cri_esco=("r_esco", "mean"),
        cri_onet=("r_onet", "mean"),
        cri_skkni=("r_skkni", "mean"),
        n_items=("source_id", "count"),
        n_complete=("cri_flag", lambda x: (x == "COMPLETE").sum()),
        n_partial=("cri_flag", lambda x: (x == "PARTIAL").sum()),
        n_incomplete=("cri_flag", lambda x: (x == "INCOMPLETE").sum()),
    ).round(4).reset_index()
    return agg


def aggregate_to_univ(cri_df: pd.DataFrame) -> pd.DataFrame:
    """Agregasi CRI dari level butir CPL ke level universitas-prodi."""
    # Buat kolom univ_prodi: "UMSU_SI", "UI_SI", "ITK_TI" dll
    cri_df = cri_df.copy()
    if "univ" not in cri_df.columns:
        cri_df["univ"] = cri_df["source_id"].apply(_extract_univ)
    cri_df["univ_prodi"] = cri_df["univ"] + "_" + cri_df["prodi"]

    # Mapping ke label yang lebih deskriptif
    UNIV_LABEL = {
        "UMSU_SI": "UMSU – Sistem Informasi",
        "UI_SI":   "UI – Sistem Informasi",
        "UMSU_TI": "UMSU – Teknologi Informasi",
        "ITK_TI":  "ITK – Informatika",
        "PENS_TI": "PENS – Teknik Komputer",
        "UGM_TI":  "UGM – Teknologi Informasi",
    }
    cri_df["univ_label"] = cri_df["univ_prodi"].map(UNIV_LABEL).fillna(cri_df["univ_prodi"])

    agg = cri_df.groupby(["univ_prodi", "univ_label", "prodi", "univ"]).agg(
        cri_mean=("cri_score", "mean"),
        cri_esco=("r_esco", "mean"),
        cri_onet=("r_onet", "mean"),
        cri_skkni=("r_skkni", "mean"),
        n_items=("source_id", "count"),
        n_complete=("cri_flag", lambda x: (x == "COMPLETE").sum()),
        n_partial=("cri_flag", lambda x: (x == "PARTIAL").sum()),
        n_incomplete=("cri_flag", lambda x: (x == "INCOMPLETE").sum()),
    ).round(4).reset_index()
    return agg


def save_cri_excel(cri_df: pd.DataFrame):
    """Simpan CRI results ke Excel dengan 4 sheet."""
    out_path = OUTPUT_DIR / "cri_results.xlsx"

    prodi_df = aggregate_to_prodi(cri_df)
    univ_df  = aggregate_to_univ(cri_df)

    # Gap analysis: sorted by cri_score ascending
    gap_df = cri_df.copy()
    gap_df["dominant_gap"] = gap_df.apply(
        lambda r: min({"ESCO": r["r_esco"], "ONET": r["r_onet"],
                       "SKKNI": r["r_skkni"]}, key=lambda k: {"ESCO": r["r_esco"],
                       "ONET": r["r_onet"], "SKKNI": r["r_skkni"]}[k]), axis=1
    )
    gap_df = gap_df.sort_values("cri_score")

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        cri_df.to_excel(writer, sheet_name="CRI_Per_CPL_Item", index=False)
        prodi_df.to_excel(writer, sheet_name="CRI_Per_Prodi", index=False)
        univ_df.to_excel(writer, sheet_name="CRI_Per_Universitas", index=False)
        gap_df[["source_id","univ","prodi","deskripsi_cpl","cri_score",
                "cri_flag","dominant_gap"]].to_excel(
            writer, sheet_name="CRI_Gap_Analysis", index=False)

    print(f"[t10] CRI Excel disimpan: {out_path}")
    print("\n[t10] === CRI SUMMARY PER UNIVERSITAS ===")
    print(univ_df[["univ_label","cri_mean","cri_esco","cri_onet","cri_skkni","n_items"]].to_string(index=False))
    return out_path


def run_cri(all_results: dict):
    """Entry point CRI computation."""
    cri_df = compute_cri(all_results)
    save_cri_excel(cri_df)
    return cri_df
