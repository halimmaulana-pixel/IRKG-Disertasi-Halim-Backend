# config.py - Pipeline IR-KG v1.1
from pathlib import Path

# Pipeline metadata
PIPELINE_VERSION = "v1.1"
PIPELINE_DATE = "2026-03-04"

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent
DATA_DIR = BACKEND_DIR / "data" / "raw"
OUTPUT_DIR = BACKEND_DIR / "data" / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "accepted_mappings").mkdir(exist_ok=True)

# ── DATA PATHS ──
PATHS = {
    "cpl_si":       DATA_DIR / "source_data/cpl_si.xlsx",
    "cpl_ti":       DATA_DIR / "source_data/cpl_ti.xlsx",
    "skkni":        DATA_DIR / "source_data/skkni_enriched.csv",
    "onet":         DATA_DIR / "source_data/onet_occupations.csv",
    "esco_skills":  DATA_DIR / "esco/esco_skills.csv",
    "esco_occ":     DATA_DIR / "esco/esco_occupations.csv",
    "occ_skill":    DATA_DIR / "graph_relations/occ_skill_relations.csv",
    "skill_skill":  DATA_DIR / "graph_relations/skill_skill_relations.csv",
    "skill_broader":DATA_DIR / "graph_relations/skill_broader_relations.csv",
    "skill_groups": DATA_DIR / "esco/esco_skill_groups.csv",
    "crosswalk":    DATA_DIR / "esco_onet_crosswalk_clean.csv",
    "bridge":       DATA_DIR / "bridge/bridge_dict.py",
}

# ── PIPELINE PARAMETERS ──
TOP_K = 20           # top-k candidates per source item
TFIDF_MAX_FEATURES = 15000
TFIDF_NGRAM_RANGE = (1, 2)
BATCH_SIZE = 100     # untuk T4/T5 batch processing

# ── 6 ABLATION CONFIGURATIONS ──
# Format: (alpha, beta, gamma, tau_strategy)
# alpha = S_sem weight, beta = S_gr weight, gamma = S_con weight
# tau_strategy: "quantile_50", "global_0.45", "zero", "quantile_75"
ABLATION_CONFIGS = {
    "v0.9": {"alpha": 1.00, "beta": 0.00, "gamma": 0.00, "tau": "quantile_50",
             "name": "Pure Semantic Baseline"},
    "v1.0": {"alpha": 0.60, "beta": 0.25, "gamma": 0.15, "tau": "quantile_50",
             "name": "Baseline Quantile-τ"},
    "v1.1": {"alpha": 0.60, "beta": 0.25, "gamma": 0.15, "tau": "zero",
             "name": "Max Accept"},
    "v1.2": {"alpha": 0.34, "beta": 0.33, "gamma": 0.33, "tau": "quantile_50",
             "name": "Balanced"},
    "v1.3": {"alpha": 0.60, "beta": 0.25, "gamma": 0.15, "tau": "quantile_75",
             "name": "Precision"},
    "v1.4": {"alpha": 0.55, "beta": 0.30, "gamma": 0.15, "tau": "quantile_50",
             "name": "Hybrid Optimal"},
}

# ── TASK DEFINITIONS ──
# Mendefinisikan setiap task secara eksplisit
TASK_DEFINITIONS = {
    "T1a": {"source": "cpl_si", "target": "esco_skills", "esco_target": True,
            "src_text_col": "bridged_text", "tgt_text_col": "skill_text"},
    "T1b": {"source": "cpl_ti", "target": "esco_skills", "esco_target": True,
            "src_text_col": "bridged_text", "tgt_text_col": "skill_text"},
    "T2a": {"source": "cpl_si", "target": "onet", "esco_target": False,
            "src_text_col": "bridged_text", "tgt_text_col": "onet_text_enriched"},
    "T2b": {"source": "cpl_ti", "target": "onet", "esco_target": False,
            "src_text_col": "bridged_text", "tgt_text_col": "onet_text_enriched"},
    "T3a": {"source": "cpl_si", "target": "skkni", "esco_target": False,
            "src_text_col": "deskripsi_cpl", "tgt_text_col": "deskripsi_unit_clean"},
    "T3b": {"source": "cpl_ti", "target": "skkni", "esco_target": False,
            "src_text_col": "deskripsi_cpl", "tgt_text_col": "deskripsi_unit_clean"},
    "T4":  {"source": "skkni", "target": "esco_skills", "esco_target": True,
            "src_text_col": "deskripsi_unit_enriched", "tgt_text_col": "skill_text"},
    "T5":  {"source": "skkni", "target": "onet", "esco_target": False,
            "src_text_col": "deskripsi_unit_enriched", "tgt_text_col": "onet_text_enriched"},
}

# ── CRI WEIGHTS ──
CRI_WEIGHTS = {"w_E": 0.40, "w_O": 0.35, "w_S": 0.25}
CRI_BASIS_CONFIG = "v1.2"   # config terbaik sebagai basis CRI

# ── OUTPUT FORMAT ──
ACCEPTED_MAPPING_COLS = [
    "source_id", "source_text", "target_id", "target_label",
    "target_type", "s_sem", "s_gr", "s_con", "s_final",
    "forced_top1", "task", "config"
]
