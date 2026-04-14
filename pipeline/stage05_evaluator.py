# stage05_evaluator.py - Pipeline IR-KG v1.1
"""
Menghitung 5 metrik evaluasi dan menghasilkan:
  1. irkg_ablation_results.xlsx (2 sheet: ESCO_Target + NonESCO_Target)
  2. irkg_score_distributions.csv
  3. irkg_evidence_paths.jsonl
  4. irkg_coverage_by_ranah_*.csv (v1.1: analisis per ranah CPL)
"""
import pandas as pd
import numpy as np
import json
from config import OUTPUT_DIR, TASK_DEFINITIONS, ABLATION_CONFIGS
from data_loader import load_cpl, load_skkni


def compute_metrics(accepted_df: pd.DataFrame,
                    all_candidates_df: pd.DataFrame,
                    task_id: str, config_id: str) -> dict:
    """
    Hitung 5 metrik:
    1. acceptance_rate = accepted / total_candidates (dengan forced=False)
    2. source_coverage = source items dengan ≥1 accepted / total source
    3. mean_final_score = mean S_final dari accepted (forced=False)
    4. forced_top1_ratio = forced / total source items
    5. selection_objective = 0.4*mean_final + 0.4*source_coverage - 0.2*forced_ratio
    """
    # Non-forced accepted
    ok = accepted_df[~accepted_df["forced_top1"]]
    forced = accepted_df[accepted_df["forced_top1"]]

    total_candidates = len(all_candidates_df)
    total_sources = all_candidates_df["source_id"].nunique()

    acceptance_rate = len(ok) / total_candidates if total_candidates > 0 else 0
    source_coverage = accepted_df["source_id"].nunique() / total_sources if total_sources > 0 else 0
    mean_final = ok["s_final"].mean() if len(ok) > 0 else 0
    forced_ratio = len(forced) / total_sources if total_sources > 0 else 0

    # Selection objective: reward coverage + precision, penalize forced
    selection_obj = 0.4 * mean_final + 0.4 * source_coverage - 0.2 * forced_ratio

    return {
        "task": task_id,
        "config": config_id,
        "config_name": ABLATION_CONFIGS[config_id]["name"],
        "esco_target": TASK_DEFINITIONS[task_id]["esco_target"],
        "acceptance_rate": round(acceptance_rate, 4),
        "source_coverage": round(source_coverage, 4),
        "mean_final_score": round(mean_final, 4),
        "forced_top1_ratio": round(forced_ratio, 4),
        "selection_objective": round(selection_obj, 4),
        "n_accepted_ok": len(ok),
        "n_accepted_forced": len(forced),
        "n_sources": total_sources,
    }


def build_ablation_table(all_results: dict,
                          all_candidates: dict) -> pd.DataFrame:
    """Build tabel ablation 8 tasks × 6 configs."""
    rows = []
    for config_id, task_results in all_results.items():
        for task_id, accepted_df in task_results.items():
            metrics = compute_metrics(
                accepted_df,
                all_candidates[task_id],
                task_id, config_id
            )
            rows.append(metrics)
    return pd.DataFrame(rows)


def save_ablation_excel(ablation_df: pd.DataFrame):
    """
    Simpan ke Excel dengan 2 sheet:
      - ESCO_Target: T1a, T1b, T4
      - NonESCO_Target: T2a, T2b, T3a, T3b, T5
    Dengan catatan footer bahwa S_final tidak comparable antar sheet.
    """
    out_path = OUTPUT_DIR / "irkg_ablation_results.xlsx"

    display_cols = ["task", "config", "config_name",
                    "acceptance_rate", "source_coverage",
                    "mean_final_score", "forced_top1_ratio", "selection_objective"]

    esco_df = ablation_df[ablation_df["esco_target"]].sort_values(["task","config"])
    nonesco_df = ablation_df[~ablation_df["esco_target"]].sort_values(["task","config"])

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        esco_df[display_cols].to_excel(writer, sheet_name="ESCO_Target", index=False)
        nonesco_df[display_cols].to_excel(writer, sheet_name="NonESCO_Target", index=False)

        # Format sheet
        for sheet_name in ["ESCO_Target", "NonESCO_Target"]:
            ws = writer.sheets[sheet_name]
            # Lebar kolom
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 18

    print(f"[stage05] Ablation Excel disimpan: {out_path}")
    return out_path


def save_evidence_paths(all_results: dict):
    """
    Simpan evidence path per accepted mapping ke JSONL.
    Format per line: {source_id, source_text, task, config,
                      target_id, target_label, s_sem, s_gr, s_con, s_final, forced}
    """
    out_path = OUTPUT_DIR / "irkg_evidence_paths.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for config_id, task_results in all_results.items():
            for task_id, accepted_df in task_results.items():
                for _, row in accepted_df.iterrows():
                    record = {
                        "source_id": row.get("source_id", ""),
                        "source_text": row.get("source_text", ""),
                        "task": task_id,
                        "config": config_id,
                        "target_id": row.get("target_id", ""),
                        "target_label": row.get("target_label", ""),
                        "target_type": row.get("target_type", ""),
                        "s_sem": float(row.get("s_sem", 0)),
                        "s_gr": float(row.get("s_gr", 0)),
                        "s_con": float(row.get("s_con", 1)),
                        "s_final": float(row.get("s_final", 0)),
                        "forced_top1": bool(row.get("forced_top1", False))
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[stage05] Evidence paths disimpan: {out_path}")


def _extract_univ(source_id: str) -> str:
    """Ekstrak kode universitas dari source_id. 'SI_UMSU_PLO-1' -> 'UMSU'"""
    parts = source_id.split("_")
    if len(parts) >= 3 and parts[1].upper() not in ("PLO",):
        return parts[1].upper()
    return "UMSU"


# v1.1+: Coverage analysis by ranah, with per-university breakdown
def analyze_coverage_by_ranah(all_results: dict,
                               basis_config: str = "v1.2") -> pd.DataFrame:
    """
    Analisis coverage accepted mappings berdasarkan ranah CPL.
    v1.2: Tambah kolom univ untuk breakdown per universitas.

    Output: irkg_coverage_by_ranah_detail.csv, irkg_coverage_by_ranah_summary.csv
    """
    cpl_si = load_cpl("SI")[["id", "ranah", "deskripsi_cpl"]]
    cpl_si["prodi"] = "SI"
    cpl_ti = load_cpl("TI")[["id", "ranah", "deskripsi_cpl"]]
    cpl_ti["prodi"] = "TI"
    cpl_all = pd.concat([cpl_si, cpl_ti], ignore_index=True)

    # Task per prodi per framework
    task_map = {
        "SI": {"ESCO": "T1a", "ONET": "T2a", "SKKNI": "T3a"},
        "TI": {"ESCO": "T1b", "ONET": "T2b", "SKKNI": "T3b"},
    }

    results = []
    cfg_results = all_results.get(basis_config, {})

    for _, cpl_row in cpl_all.iterrows():
        src_id = cpl_row["id"]
        prodi = cpl_row["prodi"]
        ranah = cpl_row["ranah"]

        row_result = {
            "source_id": src_id,
            "univ": _extract_univ(src_id),
            "prodi": prodi,
            "ranah": ranah,
            "deskripsi_cpl": cpl_row["deskripsi_cpl"][:80] + "..."
        }

        for fw, task_id in task_map[prodi].items():
            if task_id not in cfg_results:
                row_result[f"n_ok_{fw.lower()}"] = 0
                row_result[f"mean_sfinal_{fw.lower()}"] = 0.0
                row_result[f"has_mapping_{fw.lower()}"] = False
                continue

            task_df = cfg_results[task_id]
            ok = task_df[
                (task_df["source_id"] == src_id) &
                (~task_df["forced_top1"])
            ]
            n_ok = len(ok)
            row_result[f"n_ok_{fw.lower()}"] = n_ok
            row_result[f"mean_sfinal_{fw.lower()}"] = round(ok["s_final"].mean(), 4) if n_ok > 0 else 0.0
            row_result[f"has_mapping_{fw.lower()}"] = n_ok > 0

        results.append(row_result)

    detail_df = pd.DataFrame(results)

    # Agregasi per ranah
    agg_cols = [c for c in detail_df.columns if c.startswith("has_mapping_")]
    score_cols = [c for c in detail_df.columns if c.startswith("mean_sfinal_")]

    ranah_summary = detail_df.groupby("ranah").agg(
        n_items=("source_id", "count"),
        **{col: (col, "mean") for col in agg_cols},
        **{col: (col, "mean") for col in score_cols},
    ).round(4)

    # Agregasi per universitas
    univ_summary = detail_df.groupby(["univ", "prodi"]).agg(
        n_items=("source_id", "count"),
        **{col: (col, "mean") for col in agg_cols},
        **{col: (col, "mean") for col in score_cols},
    ).round(4)

    # Simpan output
    detail_path = OUTPUT_DIR / "irkg_coverage_by_ranah_detail.csv"
    summary_path = OUTPUT_DIR / "irkg_coverage_by_ranah_summary.csv"
    univ_path = OUTPUT_DIR / "irkg_coverage_by_univ.csv"
    detail_df.to_csv(detail_path, index=False)
    ranah_summary.to_csv(summary_path)
    univ_summary.to_csv(univ_path)

    print("\n[stage05] === COVERAGE PER RANAH CPL ===")
    print(f"Basis config: {basis_config}")
    print(ranah_summary.to_string())
    print("\n[stage05] === COVERAGE PER UNIVERSITAS ===")
    print(univ_summary.to_string())
    print(f"\nDetail saved: {detail_path}")
    print(f"Summary saved: {summary_path}")
    print(f"Univ saved: {univ_path}")

    return ranah_summary


def run_evaluation(all_results: dict, all_candidates: dict):
    ablation_df = build_ablation_table(all_results, all_candidates)
    save_ablation_excel(ablation_df)
    save_evidence_paths(all_results)
    print("\n[stage05] === ABLATION RESULTS SUMMARY ===")
    print(ablation_df[["task","config","selection_objective"]].pivot(
        index="config", columns="task", values="selection_objective"
    ).round(4).to_string())
    return ablation_df
