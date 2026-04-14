# stage00_domain_filter.py
"""
Stage 00: Domain Filter — S_con pre-computation untuk 6 prodi APTIKOM.

Mengklasifikasikan setiap ESCO skill terhadap domain masing-masing prodi
menggunakan strategi Hybrid ISCED Whitelist + TF-IDF:

  Tahap 1 — Eligibility Gate (semantic pre-filter):
    - Skill ada di ISCED ICT whitelist (06xx/0714) DAN sim >= MIN_SIM_WHITELIST → eligible
    - Skill TIDAK di whitelist TAPI sim >= MIN_SIM_NONWHITE (0.08) → eligible (high confidence)
    - Lainnya → outside (dibuang)

  Tahap 2 — Klasifikasi dalam pool eligible:
    s_con = 1.0  -> core     (sim >= MIN_SIM_CORE = 0.050)
    s_con = 0.5  -> adjacent (sim >= MIN_SIM_ADJ  = 0.015)
    s_con = 0.0  -> outside  (di bawah adj threshold, tidak disimpan)

Output : data/outputs/irkg_domain_filter.csv
Kolom  : prodi, node_id, s_con, domain_status, sim_score, in_whitelist, config
"""

import sys
import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import PATHS, OUTPUT_DIR

# ── KONSTANTA ────────────────────────────────────────────────────────────────
CONFIG_VERSION = "v2.1-aptikom2022"
OUTPUT_CSV     = OUTPUT_DIR / "irkg_domain_filter.csv"

# ISCED-F 2013 kode yang mendefinisikan domain computing/ICT
# 06xx = ICT broad field; 0714 = Electronics & Automation; 0541 = Mathematics (untuk CS & DS)
# Source: esco_skill_groups.csv — kolom 'code', match prefix
ISCED_ICT_CODE_PREFIXES = (
    "06",    # Information and Communication Technologies (semua 06xx)
    "0714",  # Electronics & automation
    "0541",  # Mathematics
)

# Threshold hybrid
MIN_SIM_WHITELIST = 0.010   # ISCED-tagged ICT skills: threshold masuk pool rendah
MIN_SIM_NONWHITE  = 0.080   # Skill non-ICT: harus sangat mirip untuk masuk pool
MIN_SIM_CORE      = 0.050   # Dalam pool: threshold core
MIN_SIM_ADJ       = 0.015   # Dalam pool: threshold adjacent

PRODI_LIST = ["SI", "TI", "CS", "SE", "CE", "DS"]

# ── DOMAIN DESCRIPTION PER PRODI ─────────────────────────────────────────────
# Dibangun dari domain_map_aptikom2022.py (APTIKOM 2022 + CC2020 + KKNI TIK).
# core_keywords → kata kunci bidang inti prodi
# adjacent_keywords → kata kunci pendukung lintas domain (termasuk BK bersama 21 BK)
# Keduanya digabung jadi satu teks untuk TF-IDF vectorizer.

def _build_prodi_domain_text() -> dict:
    """
    Load domain_map_aptikom2022.py dan bangun PRODI_DOMAIN_TEXT dari
    core_keywords + adjacent_keywords per prodi.
    Fallback ke hardcoded text jika file tidak ditemukan.
    """
    # Cari domain_map_aptikom2022.py relatif terhadap lokasi file ini
    _this_dir   = os.path.dirname(os.path.abspath(__file__))
    _root_dir   = os.path.dirname(_this_dir)  # backend/
    _parent_dir = os.path.dirname(_root_dir)  # irkg-webapp-v3/
    _candidates = [
        os.path.join(_root_dir,   "domain_map_aptikom2022.py"),
        os.path.join(_parent_dir, "domain_map_aptikom2022.py"),
        os.path.join(_this_dir,   "domain_map_aptikom2022.py"),
    ]

    domain_map_path = next((p for p in _candidates if os.path.exists(p)), None)

    if domain_map_path:
        import importlib.util
        spec   = importlib.util.spec_from_file_location("domain_map_aptikom2022", domain_map_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        DOMAIN_MAP = module.DOMAIN_MAP
        print(f"[Stage 00] Domain text sumber: {domain_map_path}")
        result = {}
        for prodi, cfg in DOMAIN_MAP.items():
            core_kw = cfg.get("core_keywords", [])
            adj_kw  = cfg.get("adjacent_keywords", [])
            # Gabungkan: core 2× (bobot lebih) + adjacent 1×
            combined = " ".join(core_kw * 2 + adj_kw)
            result[prodi] = combined
        return result

    # Fallback hardcoded (dipakai jika domain_map_aptikom2022.py tidak ditemukan)
    print("[Stage 00] WARNING: domain_map_aptikom2022.py tidak ditemukan — pakai fallback hardcoded")
    return _FALLBACK_DOMAIN_TEXT


# Fallback hardcoded (dipertahankan sebagai safety net)
_FALLBACK_DOMAIN_TEXT = {
    "SI": (
        "information systems management enterprise resource planning ERP customer relationship "
        "management CRM database design SQL business intelligence reporting data warehousing "
        "IT governance business analysis information architecture digital transformation "
        "workflow business process management systems integration knowledge management "
        "decision support systems enterprise architecture requirements engineering "
        "IT service management ITIL enterprise software data management IT project management"
    ),
    "TI": (
        "network engineering network administration cybersecurity cloud computing DevOps "
        "TCP/IP networking penetration testing security operations cloud infrastructure "
        "system administration Linux Windows Server containerization Docker Kubernetes "
        "Internet of Things embedded systems virtualization incident response digital forensics"
    ),
    "CS": (
        "algorithm design computational complexity data structures automata theory "
        "programming language theory compiler design functional programming discrete mathematics "
        "artificial intelligence machine learning deep learning neural networks computer vision "
        "natural language processing scientific computing mathematical logic formal methods"
    ),
    "SE": (
        "software engineering software development lifecycle agile scrum requirements engineering "
        "software architecture design patterns software testing quality assurance DevOps CI/CD "
        "software project management code review refactoring test-driven development "
        "software quality microservices full stack development web development mobile development"
    ),
    "CE": (
        "computer architecture digital systems design FPGA ASIC VHDL Verilog embedded systems "
        "microcontroller firmware RTOS real-time systems Internet of Things sensor design "
        "robotics automation control systems hardware description language device drivers "
        "PCB design signal processing hardware security wireless sensor networks"
    ),
    "DS": (
        "data science machine learning deep learning statistical analysis data visualization "
        "big data Apache Spark Hadoop data pipeline ETL feature engineering model evaluation "
        "natural language processing computer vision business intelligence Tableau Power BI "
        "bayesian statistics regression classification clustering dimensionality reduction"
    ),
}

PRODI_DOMAIN_TEXT = _build_prodi_domain_text()


# ── HELPER: Build ISCED ICT Whitelist ────────────────────────────────────────

def build_isced_whitelist() -> set:
    """
    Bangun set URI skill ESCO yang termasuk dalam ISCED ICT domain.

    Metode:
    1. Load esco_skill_groups.csv → ambil semua group URI dengan kode 06xx / 0714 / 0541
    2. Load skill_broader_relations.csv → ambil semua skill yang broaderUri-nya
       adalah salah satu group ICT tersebut

    Returns set of skill conceptUri strings.
    """
    groups_path  = PATHS.get("skill_groups")
    broader_path = PATHS.get("skill_broader")

    if not groups_path or not groups_path.exists():
        print("[Stage 00] WARNING: esco_skill_groups.csv tidak ditemukan — whitelist kosong")
        return set()
    if not broader_path or not broader_path.exists():
        print("[Stage 00] WARNING: skill_broader_relations.csv tidak ditemukan — whitelist kosong")
        return set()

    # Step 1: ambil ISCED ICT group URIs
    groups_df = pd.read_csv(groups_path)
    ict_mask  = (
        groups_df["code"].notna()
        & groups_df["code"].astype(str).str.match(
            r"^(" + "|".join(ISCED_ICT_CODE_PREFIXES) + r")"
        )
    )
    ict_group_uris = set(groups_df.loc[ict_mask, "conceptUri"].tolist())
    print(f"[Stage 00] ISCED ICT group codes: "
          f"{sorted(groups_df.loc[ict_mask,'code'].tolist())} ({len(ict_group_uris)} groups)")

    # Step 2: ambil skills yang broader-nya adalah group ICT
    broader_df = pd.read_csv(broader_path)
    skill_mask = broader_df["broaderUri"].isin(ict_group_uris)
    whitelist  = set(broader_df.loc[skill_mask, "conceptUri"].tolist())
    print(f"[Stage 00] ISCED ICT whitelist: {len(whitelist)} skill URIs")
    return whitelist


# ── MAIN FUNCTION ─────────────────────────────────────────────────────────────

def run_domain_filter() -> pd.DataFrame:
    """
    Jalankan domain filter untuk 6 prodi dengan strategi Hybrid ISCED + TF-IDF.
    Returns DataFrame hasil klasifikasi (core + adjacent saja).
    """
    print("[Stage 00] Domain Filter v2.0 — Hybrid ISCED Whitelist + TF-IDF")
    print(f"[Stage 00] Thresholds: whitelist_min={MIN_SIM_WHITELIST}, "
          f"nonwhite_min={MIN_SIM_NONWHITE}, core={MIN_SIM_CORE}, adj={MIN_SIM_ADJ}")

    # ── 1. Build ISCED whitelist
    ict_whitelist = build_isced_whitelist()

    # ── 2. Load ESCO skills
    esco_df = pd.read_csv(PATHS["esco_skills"])
    esco_df["description"] = esco_df["description"].fillna("")
    esco_df["skill_text"]  = esco_df["preferredLabel"] + " " + esco_df["description"]

    esco_ids   = esco_df["conceptUri"].tolist()
    esco_texts = esco_df["skill_text"].tolist()
    n_esco     = len(esco_ids)

    # Precompute whitelist membership sebagai boolean array
    in_whitelist = np.array([uri in ict_whitelist for uri in esco_ids], dtype=bool)
    print(f"[Stage 00] ESCO skills loaded: {n_esco}  (whitelist hits: {in_whitelist.sum()})")

    # ── 3. Fit TF-IDF vectorizer pada seluruh corpus ESCO
    print("[Stage 00] Fitting TF-IDF vectorizer...")
    vectorizer = TfidfVectorizer(
        max_features=25000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
        strip_accents="unicode",
        analyzer="word",
    )
    esco_matrix = vectorizer.fit_transform(esco_texts)
    print(f"[Stage 00] TF-IDF matrix: {esco_matrix.shape[0]} x {esco_matrix.shape[1]}")

    all_rows = []

    for prodi in PRODI_LIST:
        domain_vec = vectorizer.transform([PRODI_DOMAIN_TEXT[prodi]])
        sims       = cosine_similarity(domain_vec, esco_matrix).flatten().astype(float)

        # ── Eligibility gate (Tahap 1)
        # Skill masuk pool jika:
        #   (a) ada di ISCED ICT whitelist DAN sim cukup rendah pun lolos, ATAU
        #   (b) tidak di whitelist tapi sim SANGAT tinggi (0.08+) — extra-domain excellence
        eligible = (in_whitelist & (sims >= MIN_SIM_WHITELIST)) | (~in_whitelist & (sims >= MIN_SIM_NONWHITE))

        n_core = n_adj = n_out = 0
        for esco_id, sim, is_wl, is_eligible in zip(esco_ids, sims, in_whitelist, eligible):
            if not is_eligible:
                n_out += 1
                continue

            sim_f = float(sim)
            if sim_f >= MIN_SIM_CORE:
                all_rows.append({
                    "prodi":         prodi,
                    "node_id":       esco_id,
                    "s_con":         1.0,
                    "domain_status": "core",
                    "sim_score":     round(sim_f, 6),
                    "in_whitelist":  bool(is_wl),
                    "config":        CONFIG_VERSION,
                })
                n_core += 1
            elif sim_f >= MIN_SIM_ADJ:
                all_rows.append({
                    "prodi":         prodi,
                    "node_id":       esco_id,
                    "s_con":         0.5,
                    "domain_status": "adjacent",
                    "sim_score":     round(sim_f, 6),
                    "in_whitelist":  bool(is_wl),
                    "config":        CONFIG_VERSION,
                })
                n_adj += 1
            else:
                # Eligible tapi sim terlalu rendah untuk adj → outside
                n_out += 1

        n_eligible = int(eligible.sum())
        print(
            f"[Stage 00]   {prodi}: eligible={n_eligible:>4}  "
            f"core={n_core:>4}  adjacent={n_adj:>4}  outside={n_out:>5}"
        )

    df = pd.DataFrame(all_rows)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"[Stage 00] Output: {len(df)} rows -> {OUTPUT_CSV.name}")
    print("[Stage 00] Selesai.")
    return df


if __name__ == "__main__":
    run_domain_filter()
