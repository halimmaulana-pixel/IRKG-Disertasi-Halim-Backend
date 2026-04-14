# stage04_scorer.py
"""
Hybrid scoring + S_con + acceptance gate.

Formula:
  ESCO-target tasks: S_final = alpha·S_sem + beta·S_gr + gamma·S_con
  NonESCO tasks:     S_final = alpha_eff·S_sem + gamma_eff·S_con
    dimana alpha_eff = alpha/(alpha+gamma), gamma_eff = gamma/(alpha+gamma), beta_eff = 0

S_con (Constraint Score) dari domain_filter_results (Stage 00):
  = 1.0 -> core domain
  = 0.5 -> adjacent domain
  = 0.0 -> outside domain (tidak ada di domain filter)
  Non-ESCO targets (ONET/SKKNI): default 1.0 (sudah dalam domain computing)

Acceptance Gate:
  tau_strategy = "quantile_50": tau = median S_final dari semua candidates
  tau_strategy = "global_0.45": tau = 0.45 fixed
  tau_strategy = "zero":        tau = 0 (accept all)
  tau_strategy = "quantile_75": tau = 75th percentile S_final

FORCED_TOP1:
  Jika tidak ada accepted mapping (semua < tau),
  ambil candidate dengan S_final tertinggi -> set forced_top1 = True
"""
import pandas as pd
import numpy as np
from config import ABLATION_CONFIGS, TASK_DEFINITIONS, OUTPUT_DIR, ACCEPTED_MAPPING_COLS
from data_loader import load_cpl, load_skkni

# ── Domain filter lookup (loaded once at module import) ───────────────────────
# Key: (prodi, node_id) -> s_con float
_DOMAIN_LOOKUP: dict = {}
# Key: node_id -> max s_con across all prodi (for T4: SKKNI->ESCO)
_DOMAIN_ANY: dict = {}

def _load_domain_filter_lookup():
    filter_path = OUTPUT_DIR / "irkg_domain_filter.csv"
    if not filter_path.exists():
        print("[Stage 04] WARNING: irkg_domain_filter.csv tidak ditemukan — s_con default 1.0")
        return
    df = pd.read_csv(filter_path)
    for _, row in df.iterrows():
        _DOMAIN_LOOKUP[(str(row["prodi"]), str(row["node_id"]))] = float(row["s_con"])
    for node_id, grp in df.groupby("node_id"):
        _DOMAIN_ANY[str(node_id)] = float(grp["s_con"].max())
    print(f"[Stage 04] Domain filter loaded: {len(df)} rows, "
          f"{len(_DOMAIN_LOOKUP)} (prodi,skill) pairs, {len(_DOMAIN_ANY)} unique skills")

_load_domain_filter_lookup()

# Mapping task_id -> prodi untuk ESCO-target tasks dengan prodi spesifik
_TASK_PRODI = {"T1a": "SI", "T1b": "TI"}


def compute_s_con(target_type: str, target_id: str, task_id: str = None) -> float:
    """Compute constraint score dari domain_filter_results (Stage 00).

    ESCO targets:
      - T1a (CPL SI -> ESCO): lookup prodi=SI
      - T1b (CPL TI -> ESCO): lookup prodi=TI
      - T4  (SKKNI -> ESCO):  max s_con across any prodi
    Non-ESCO targets (ONET, SKKNI): default 1.0
    """
    if target_type != "ESCO":
        return 1.0

    if not _DOMAIN_LOOKUP:
        return 1.0  # fallback jika domain filter belum diload

    if task_id in _TASK_PRODI:
        key = (_TASK_PRODI[task_id], target_id)
        return _DOMAIN_LOOKUP.get(key, 0.0)
    elif task_id == "T4":
        return _DOMAIN_ANY.get(target_id, 0.0)
    # Fallback untuk task lain dengan ESCO target
    return _DOMAIN_ANY.get(target_id, 0.0)


def compute_tau(s_final_values: np.ndarray, strategy: str) -> float:
    """Compute acceptance threshold berdasarkan strategi."""
    if strategy == "quantile_50":
        return float(np.median(s_final_values))
    elif strategy == "global_0.45":
        return 0.45
    elif strategy == "zero":
        return 0.0
    elif strategy == "quantile_75":
        return float(np.percentile(s_final_values, 75))
    else:
        raise ValueError(f"Unknown tau strategy: {strategy}")


def compute_s_final(row: pd.Series, alpha: float, beta: float,
                    gamma: float, is_esco_target: bool) -> float:
    """Compute S_final untuk satu candidate."""
    s_sem = row["s_sem"]
    s_gr = row["s_gr"]
    s_con = row.get("s_con", 1.0)

    if is_esco_target:
        return alpha * s_sem + beta * s_gr + gamma * s_con
    else:
        # Renormalize: beta = 0
        denom = alpha + gamma
        if denom == 0:
            return 0.0
        a_eff = alpha / denom
        g_eff = gamma / denom
        return a_eff * s_sem + g_eff * s_con


def run_scorer_for_config(candidates_with_sgr: dict,
                          config_id: str) -> dict:
    """
    Jalankan scoring + acceptance gate untuk satu ablation config.
    Returns dict {task_id: DataFrame accepted_mappings}
    """
    cfg = ABLATION_CONFIGS[config_id]
    alpha = cfg["alpha"]
    beta = cfg["beta"]
    gamma = cfg["gamma"]
    tau_strategy = cfg["tau"]

    # Load source texts untuk output
    cpl_si = load_cpl("SI").set_index("id")
    cpl_ti = load_cpl("TI").set_index("id")
    skkni = load_skkni().set_index("id")

    accepted_all = {}

    for task_id, candidates in candidates_with_sgr.items():
        is_esco = TASK_DEFINITIONS[task_id]["esco_target"]
        df = candidates.copy()

        # Compute S_con dari domain_filter (Stage 00)
        df["s_con"] = df.apply(
            lambda r: compute_s_con(r["target_type"], r["target_id"], task_id), axis=1
        )

        # Compute S_final
        df["s_final"] = df.apply(
            lambda r: compute_s_final(r, alpha, beta, gamma, is_esco), axis=1
        )
        df["s_final"] = df["s_final"].round(6)

        # Compute threshold
        tau = compute_tau(df["s_final"].values, tau_strategy)

        # Acceptance gate per source item
        accepted_rows = []
        for src_id, group in df.groupby("source_id"):
            group_sorted = group.sort_values("s_final", ascending=False)

            # Accepted: s_final >= tau
            accepted = group_sorted[group_sorted["s_final"] >= tau].copy()
            accepted["forced_top1"] = False

            if len(accepted) == 0:
                # FORCED_TOP1: ambil yang terbaik
                top1 = group_sorted.head(1).copy()
                top1["forced_top1"] = True
                accepted_rows.append(top1)
            else:
                accepted_rows.append(accepted)

        accepted_df = pd.concat(accepted_rows, ignore_index=True)

        # Tambah source_text
        def get_source_text(src_id):
            if src_id.startswith("SI_"):
                return cpl_si.loc[src_id, "deskripsi_cpl"] if src_id in cpl_si.index else ""
            elif src_id.startswith("TI_"):
                return cpl_ti.loc[src_id, "deskripsi_cpl"] if src_id in cpl_ti.index else ""
            else:
                return skkni.loc[src_id, "judul_unit"] if src_id in skkni.index else ""

        accepted_df["source_text"] = accepted_df["source_id"].apply(get_source_text)
        accepted_df["task"] = task_id
        accepted_df["config"] = config_id

        # Simpan ke CSV
        out_path = OUTPUT_DIR / "accepted_mappings" / \
                   f"irkg_accepted_{task_id}_{config_id}.csv"
        cols_to_save = [c for c in ACCEPTED_MAPPING_COLS if c in accepted_df.columns]
        accepted_df[cols_to_save].to_csv(out_path, index=False)

        print(f"  [{task_id}][{config_id}] tau={tau:.4f}, "
              f"accepted={len(accepted_df)}, "
              f"forced={accepted_df['forced_top1'].sum()}")

        accepted_all[task_id] = accepted_df

    return accepted_all


def run_all_configs(candidates_with_sgr: dict) -> dict:
    """Jalankan scoring untuk semua 6 configs. Returns {config_id: {task_id: df}}"""
    all_results = {}
    for config_id in ABLATION_CONFIGS:
        print(f"\n=== Config: {config_id} ({ABLATION_CONFIGS[config_id]['name']}) ===")
        all_results[config_id] = run_scorer_for_config(candidates_with_sgr, config_id)
    return all_results
