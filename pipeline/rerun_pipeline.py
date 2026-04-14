"""
Re-run pipeline Stage 02 -> Stage 06 + CRI
Stage 00 dan 01 di-skip (pakai domain filter v2.1-aptikom2022 + pkl vectorizer yang ada)
"""
import time, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR, ABLATION_CONFIGS
import stage01_preprocess as s01
import stage02_candidates  as s02
import stage03_graph       as s03
import stage04_scorer      as s04
import stage05_evaluator   as s05
import stage06_ecv         as s06
import t10_cri

start = time.time()
print("=" * 60)
print("IR-KG PIPELINE RE-RUN (Stage 02 onwards)")
print("Stage 00: SKIP (domain filter v2.1-aptikom2022 sudah ada)")
print("Stage 01: LOAD dari pkl yang tersimpan")
print("=" * 60)

# Stage 01: Load dari pkl
print("\n[Stage 01] Loading vectorizers dari pkl...")
vectorizers = s01.load_all_vectorizers()
print(f"  Loaded {len(vectorizers)} vectorizers")

# Stage 02: Generate candidates
print("\n[Stage 02] Generating top-k candidates...")
all_candidates = s02.run_all_candidate_generation(vectorizers)

# Stage 03: S_gr
print("\n[Stage 03] Computing S_gr...")
candidates_with_sgr = s03.compute_sgr_all_tasks(all_candidates)

# Stage 04: Hybrid scoring semua 6 config
print("\n[Stage 04] Hybrid scoring + acceptance gate (6 configs)...")
all_results = {}
for cfg_id in ABLATION_CONFIGS.keys():
    print(f"  Config: {cfg_id}")
    all_results[cfg_id] = s04.run_scorer_for_config(candidates_with_sgr, cfg_id)

# Stage 05: Evaluation + ablation table
print("\n[Stage 05] Computing metrics...")
ablation_df = s05.run_evaluation(all_results, all_candidates)
s05.analyze_coverage_by_ranah(all_results, basis_config="v1.2")

# Stage 06: ECV
print("\n[Stage 06] External Consistency Validation...")
s06.run_ecv(all_results)

# T10: CRI
print("\n[t10] Career Readiness Index...")
t10_cri.run_cri(all_results)

elapsed = time.time() - start
print(f"\n[Pipeline] Selesai dalam {elapsed:.1f}s")

summary = {
    "version": "v1.1-rerun",
    "stage00_config": "v2.1-aptikom2022",
    "tasks_run": list(all_candidates.keys()),
    "configs_run": list(ABLATION_CONFIGS.keys()),
    "elapsed_seconds": round(elapsed, 1),
    "n_accepted_total": sum(len(df) for cfg in all_results.values() for df in cfg.values())
}
with open(OUTPUT_DIR / "irkg_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("Summary:", summary)
